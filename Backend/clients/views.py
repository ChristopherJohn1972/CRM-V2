import logging
from datetime import datetime, timezone

import sqlalchemy as sa
from django.conf import settings
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from clients.access import can_access_customer, scope_queryset
from clients.models import (
    Customer,
    CustomerAddress,
    CustomerContact,
    CustomerRelationship,
    RelationshipType,
)
from clients.serializers import (
    AddressSerializer,
    ContactSerializer,
    ContactWriteSerializer,
    CustomerSerializer,
    CustomerWriteSerializer,
    OwnershipTransferSerializer,
    RelationshipSerializer,
    StatusChangeSerializer,
)
from clients.services import CustomerService
from common import audit
from common.db import SessionLocal
from common.events import DomainEvent, EventBus
from common.exceptions import NotFoundError, PermissionDeniedError
from iam.permissions import HasPermission, PermissionRequiredMixin, UserPrincipal

logger = logging.getLogger(__name__)

PERMISSION_CUSTOMER_READ = "clients.customer.read"
PERMISSION_CUSTOMER_CREATE = "clients.customer.create"
PERMISSION_CUSTOMER_UPDATE = "clients.customer.update"
PERMISSION_CUSTOMER_STATUS = "clients.customer.status.change"
PERMISSION_CUSTOMER_OWNERSHIP = "clients.customer.ownership.transfer"
PERMISSION_CUSTOMER_SENSITIVE = "clients.customer.sensitive.read"
PERMISSION_CONTACT_CREATE = "clients.contact.create"
PERMISSION_CONTACT_UPDATE = "clients.contact.update"
PERMISSION_CONTACT_DELETE = "clients.contact.delete"
PERMISSION_RELATIONSHIP_CREATE = "clients.relationship.create"
PERMISSION_RELATIONSHIP_DELETE = "clients.relationship.delete"
PERMISSION_ADDRESS_WRITE = "clients.address.write"
PERMISSION_CUSTOMER_DELETE = "clients.customer.delete"
PERMISSION_PORTAL_CREDENTIAL_ACCESS = "portal.credential.read"
PERMISSION_PORTAL_CREDENTIAL_RESET = "portal.credential.reset"


def _principal(request) -> UserPrincipal:
    return getattr(request, "user", None)


def _require_permission(principal, code):
    if principal is None or not principal.has_permission(code):
        raise PermissionDeniedError(f"Missing required permission: {code}")


def _get_customer(db, request, customer_id):
    customer = db.get(Customer, customer_id)
    if customer is None or customer.deleted_at is not None:
        raise NotFoundError("Customer not found.")
    if not can_access_customer(db, _principal(request), customer):
        raise PermissionDeniedError()
    return customer


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class CustomerListView(APIView):
    def get(self, request):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CUSTOMER_READ)

        session = SessionLocal()
        try:
            stmt = sa.select(Customer).where(Customer.deleted_at.is_(None))
            stmt = scope_queryset(session, principal, stmt)

            search = request.query_params.get("search")
            if search:
                like = f"%{search}%"
                stmt = stmt.where(
                    sa.or_(
                        Customer.legal_name.like(like),
                        Customer.first_name.like(like),
                        Customer.last_name.like(like),
                        Customer.customer_number.like(like),
                    )
                )
            customer_type = request.query_params.get("customer_type")
            if customer_type:
                stmt = stmt.where(Customer.customer_type == customer_type)
            customer_status = request.query_params.get("status")
            if customer_status:
                stmt = stmt.where(Customer.status == customer_status)
            segment = request.query_params.get("segment")
            if segment:
                stmt = stmt.where(Customer.segment == segment)

            stmt = stmt.order_by(sa.desc(Customer.customer_id))
            total = session.execute(
                sa.select(sa.func.count()).select_from(stmt.subquery())
            ).scalar()

            paginator = PageNumberPagination()
            page_size = paginator.get_page_size(request) or settings.REST_FRAMEWORK.get("PAGE_SIZE", 20)
            try:
                page_number = int(request.query_params.get(paginator.page_query_param, 1))
            except (TypeError, ValueError):
                page_number = 1
            page_number = max(1, page_number)

            rows = session.execute(
                stmt.limit(page_size).offset((page_number - 1) * page_size)
            ).scalars().all()

            data = CustomerSerializer(rows, many=True, context={"principal": principal}).data
            return Response(
                {
                    "count": total,
                    "page": page_number,
                    "page_size": page_size,
                    "results": data,
                }
            )
        finally:
            session.close()

    def post(self, request):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CUSTOMER_CREATE)

        serializer = CustomerWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = dict(serializer.validated_data)
        addresses = payload.pop("addresses", None)

        session = SessionLocal()
        try:
            customer = CustomerService.create_customer(
                session, payload, principal.user_id, request=request
            )

            if addresses:
                for address in addresses:
                    address["customer_id"] = customer.customer_id
                    session.add(CustomerAddress(**address))
                session.commit()

            data = CustomerSerializer(customer, context={"principal": principal}).data
            data["_360_url"] = f"/api/clients/{customer.customer_id}/360"
            if getattr(customer, "_temp_portal_password", None):
                data["portal_access"] = {
                    "username": customer.customer_number,
                    "temp_password": customer._temp_portal_password,
                    "message": "Portal access created. Share the temporary password securely. The customer must change it on first login.",
                }
            return Response(data, status=status.HTTP_201_CREATED)
        finally:
            session.close()


class CustomerDetailView(APIView):
    def get(self, request, customer_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CUSTOMER_READ)

        session = SessionLocal()
        try:
            customer = _get_customer(session, request, customer_id)
            data = CustomerSerializer(customer, context={"principal": principal}).data
            data["_360_url"] = f"/api/clients/{customer.customer_id}/360"

            data["permissions"] = {
                "can_edit": principal.has_permission(PERMISSION_CUSTOMER_UPDATE),
                "can_delete": principal.has_permission(PERMISSION_CUSTOMER_DELETE),
                "can_change_status": principal.has_permission(PERMISSION_CUSTOMER_STATUS),
                "can_manage_portal": principal.has_permission(PERMISSION_PORTAL_CREDENTIAL_ACCESS),
            }
            return Response(data)
        finally:
            session.close()

    def patch(self, request, customer_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CUSTOMER_UPDATE)

        serializer = CustomerWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        payload = dict(serializer.validated_data)
        payload.pop("addresses", None)

        session = SessionLocal()
        try:
            customer = _get_customer(session, request, customer_id)
            if payload.get("customer_type") and payload["customer_type"] != customer.customer_type:
                raise PermissionDeniedError("Changing customer type is not allowed.")
            customer = CustomerService.update_customer(
                session, customer, payload, principal.user_id, request=request
            )
            data = CustomerSerializer(customer, context={"principal": principal}).data
            return Response(data)
        finally:
            session.close()

    def delete(self, request, customer_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CUSTOMER_DELETE)

        session = SessionLocal()
        try:
            customer = _get_customer(session, request, customer_id)

            now = _utcnow()

            audit.record_audit(
                session,
                actor_user_id=principal.user_id,
                action="customer.permanently_deleted",
                resource_type="customers",
                resource_id=customer.customer_id,
                description=f"Customer {customer.customer_number} permanently deleted",
                metadata={
                    "account_number": customer.customer_number,
                    "customer_type": customer.customer_type,
                    "legal_name": customer.legal_name,
                },
                request=request,
            )

            from portal.models import CustomerAccount, PortalUserCustomer
            from communications.models import SmsMessage, EmailMessage, CallLog
            from activities.models import Activity

            customer_account = session.execute(
                sa.select(CustomerAccount).where(CustomerAccount.customer_id == customer_id)
            ).scalar_one_or_none()

            if customer_account:
                session.execute(
                    sa.delete(PortalUserCustomer).where(
                        PortalUserCustomer.customer_account_id == customer_account.customer_account_id
                    )
                )
                session.delete(customer_account)

            session.execute(sa.delete(Activity).where(Activity.customer_id == customer_id))
            session.execute(sa.delete(SmsMessage).where(SmsMessage.customer_id == customer_id))
            session.execute(sa.delete(EmailMessage).where(EmailMessage.customer_id == customer_id))
            session.execute(sa.delete(CallLog).where(CallLog.customer_id == customer_id))

            session.delete(customer)
            session.commit()

            EventBus.publish(
                DomainEvent(
                    event_type="CustomerPermanentlyDeleted",
                    customer_id=customer_id,
                    source_module="clients",
                    actor_user_id=principal.user_id,
                    actor_type="INTERNAL_USER",
                    summary=f"Customer {customer.customer_number} permanently deleted",
                    reference_type="customers",
                    reference_id=customer_id,
                )
            )
            return Response(status=status.HTTP_204_NO_CONTENT)
        finally:
            session.close()


class CustomerActionView(APIView):
    action = None

    def post(self, request, customer_id):
        principal = _principal(request)
        session = SessionLocal()
        try:
            customer = _get_customer(session, request, customer_id)

            if self.action == "status":
                _require_permission(principal, PERMISSION_CUSTOMER_STATUS)
                serializer = StatusChangeSerializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                customer = CustomerService.change_status(
                    session,
                    customer,
                    serializer.validated_data["status"],
                    serializer.validated_data.get("reason"),
                    principal.user_id,
                    request=request,
                )
            elif self.action == "close":
                _require_permission(principal, PERMISSION_CUSTOMER_STATUS)
                customer = CustomerService.change_status(
                    session,
                    customer,
                    "CLOSED",
                    request.data.get("reason"),
                    principal.user_id,
                    request=request,
                )
            elif self.action == "transfer":
                _require_permission(principal, PERMISSION_CUSTOMER_OWNERSHIP)
                serializer = OwnershipTransferSerializer(data=request.data)
                serializer.is_valid(raise_exception=True)
                customer = CustomerService.transfer_ownership(
                    session,
                    customer,
                    serializer.validated_data.get("assigned_user_id"),
                    serializer.validated_data.get("assigned_team_id"),
                    principal.user_id,
                    request=request,
                )
            else:
                raise NotFoundError("Unknown action.")

            return Response(CustomerSerializer(customer, context={"principal": principal}).data)
        finally:
            session.close()


class CustomerContactListView(APIView):
    def get(self, request, customer_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CUSTOMER_READ)
        session = SessionLocal()
        try:
            _get_customer(session, request, customer_id)
            rows = session.execute(
                sa.select(CustomerContact)
                .where(
                    CustomerContact.customer_id == customer_id,
                    CustomerContact.is_active == sa.true(),
                )
                .order_by(sa.desc(CustomerContact.contact_id))
            ).scalars().all()
            return Response(ContactSerializer(rows, many=True).data)
        finally:
            session.close()

    def post(self, request, customer_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CONTACT_CREATE)
        serializer = ContactWriteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = SessionLocal()
        try:
            _get_customer(session, request, customer_id)
            contact = CustomerContact(customer_id=customer_id, **serializer.validated_data)
            if contact.is_primary:
                session.execute(
                    sa.update(CustomerContact)
                    .where(CustomerContact.customer_id == customer_id)
                    .values(is_primary=False)
                )
            session.add(contact)
            session.flush()
            audit.record_audit(
                session,
                actor_user_id=principal.user_id,
                action="contact.created",
                resource_type="customer_contacts",
                resource_id=contact.contact_id,
                description=f"Contact {contact.first_name} {contact.last_name} added to customer {customer_id}",
                request=request,
            )
            session.commit()
            session.refresh(contact)
            EventBus.publish(
                DomainEvent(
                    event_type="ContactAdded",
                    customer_id=customer_id,
                    source_module="clients",
                    actor_user_id=principal.user_id,
                    actor_type="INTERNAL_USER",
                    summary=f"Contact {contact.first_name} {contact.last_name} added",
                    reference_type="customer_contacts",
                    reference_id=contact.contact_id,
                )
            )
            return Response(ContactSerializer(contact).data, status=status.HTTP_201_CREATED)
        finally:
            session.close()


class CustomerContactDetailView(APIView):
    def _get_contact(self, session, request, customer_id, contact_id):
        _get_customer(session, request, customer_id)
        contact = session.get(CustomerContact, contact_id)
        if contact is None or contact.customer_id != customer_id:
            raise NotFoundError("Contact not found.")
        return contact

    def patch(self, request, customer_id, contact_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CONTACT_UPDATE)
        serializer = ContactWriteSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        session = SessionLocal()
        try:
            contact = self._get_contact(session, request, customer_id, contact_id)
            if serializer.validated_data.get("is_primary"):
                session.execute(
                    sa.update(CustomerContact)
                    .where(CustomerContact.customer_id == customer_id)
                    .values(is_primary=False)
                )
            for key, value in serializer.validated_data.items():
                setattr(contact, key, value)
            audit.record_audit(
                session,
                actor_user_id=principal.user_id,
                action="contact.updated",
                resource_type="customer_contacts",
                resource_id=contact.contact_id,
                description=f"Contact {contact_id} updated",
                request=request,
            )
            session.commit()
            session.refresh(contact)
            return Response(ContactSerializer(contact).data)
        finally:
            session.close()

    def delete(self, request, customer_id, contact_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CONTACT_DELETE)
        session = SessionLocal()
        try:
            contact = self._get_contact(session, request, customer_id, contact_id)
            contact.is_active = False
            audit.record_audit(
                session,
                actor_user_id=principal.user_id,
                action="contact.deactivated",
                resource_type="customer_contacts",
                resource_id=contact.contact_id,
                description=f"Contact {contact_id} deactivated",
                request=request,
            )
            session.commit()
            return Response(status=status.HTTP_204_NO_CONTENT)
        finally:
            session.close()


class CustomerRelationshipListView(APIView):
    def get(self, request, customer_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CUSTOMER_READ)
        session = SessionLocal()
        try:
            _get_customer(session, request, customer_id)
            rows = session.execute(
                sa.select(CustomerRelationship).where(
                    CustomerRelationship.customer_id == customer_id
                )
            ).scalars().all()
            related_ids = {row.related_customer_id for row in rows}
            related_map = {}
            if related_ids:
                related_map = {
                    c.customer_id: c
                    for c in session.execute(
                        sa.select(Customer).where(
                            Customer.customer_id.in_(related_ids),
                            Customer.deleted_at.is_(None),
                        )
                    ).scalars().all()
                }
            return Response(
                RelationshipSerializer(rows, many=True, context={"related_map": related_map}).data
            )
        finally:
            session.close()

    def post(self, request, customer_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_RELATIONSHIP_CREATE)
        session = SessionLocal()
        try:
            _get_customer(session, request, customer_id)
            related_customer_id = request.data.get("related_customer_id")
            relationship_type = request.data.get("relationship_type")
            description = request.data.get("description")

            if not related_customer_id or not relationship_type:
                raise NotFoundError("related_customer_id and relationship_type are required.")
            if int(related_customer_id) == customer_id:
                raise PermissionDeniedError("A customer cannot be related to itself.")

            related = session.get(Customer, int(related_customer_id))
            if related is None:
                raise NotFoundError("Related customer not found.")
            if not can_access_customer(session, principal, related):
                raise PermissionDeniedError("No access to the related customer.")

            relationship_type_row = session.execute(
                sa.select(RelationshipType).where(
                    RelationshipType.code == relationship_type,
                    RelationshipType.is_active == sa.true(),
                )
            ).scalar_one_or_none()
            if relationship_type_row is None:
                raise NotFoundError("Relationship type is not configured.")

            relationship = CustomerRelationship(
                customer_id=customer_id,
                related_customer_id=int(related_customer_id),
                relationship_type=relationship_type,
                description=description,
            )
            session.add(relationship)
            session.flush()
            audit.record_audit(
                session,
                actor_user_id=principal.user_id,
                action="relationship.created",
                resource_type="customer_relationships",
                resource_id=relationship.relationship_id,
                description=f"Relationship {relationship_type} added to customer {customer_id}",
                request=request,
            )
            session.commit()
            session.refresh(relationship)
            return Response(
                RelationshipSerializer(relationship, context={"related_map": {related.customer_id: related}}).data,
                status=status.HTTP_201_CREATED,
            )
        finally:
            session.close()


class CustomerRelationshipDetailView(APIView):
    def delete(self, request, customer_id, relationship_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_RELATIONSHIP_DELETE)
        session = SessionLocal()
        try:
            _get_customer(session, request, customer_id)
            relationship = session.get(CustomerRelationship, relationship_id)
            if relationship is None or relationship.customer_id != customer_id:
                raise NotFoundError("Relationship not found.")
            audit.record_audit(
                session,
                actor_user_id=principal.user_id,
                action="relationship.deleted",
                resource_type="customer_relationships",
                resource_id=relationship.relationship_id,
                description=f"Relationship {relationship.relationship_type} removed from customer {customer_id}",
                request=request,
            )
            session.delete(relationship)
            session.commit()
            return Response(status=status.HTTP_204_NO_CONTENT)
        finally:
            session.close()


class CustomerAddressListView(APIView):
    def get(self, request, customer_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CUSTOMER_READ)
        session = SessionLocal()
        try:
            _get_customer(session, request, customer_id)
            rows = session.execute(
                sa.select(CustomerAddress).where(
                    CustomerAddress.customer_id == customer_id
                )
            ).scalars().all()
            return Response(AddressSerializer(rows, many=True).data)
        finally:
            session.close()

    def post(self, request, customer_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_ADDRESS_WRITE)
        serializer = AddressSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        session = SessionLocal()
        try:
            _get_customer(session, request, customer_id)
            address = CustomerAddress(customer_id=customer_id, **serializer.validated_data)
            if address.is_primary:
                session.execute(
                    sa.update(CustomerAddress)
                    .where(CustomerAddress.customer_id == customer_id)
                    .values(is_primary=False)
                )
            session.add(address)
            session.commit()
            session.refresh(address)
            return Response(AddressSerializer(address).data, status=status.HTTP_201_CREATED)
        finally:
            session.close()


class CustomerAddressDetailView(APIView):
    def _get_address(self, session, request, customer_id, address_id):
        _get_customer(session, request, customer_id)
        address = session.get(CustomerAddress, address_id)
        if address is None or address.customer_id != customer_id:
            raise NotFoundError("Address not found.")
        return address

    def patch(self, request, customer_id, address_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_ADDRESS_WRITE)
        serializer = AddressSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        session = SessionLocal()
        try:
            address = self._get_address(session, request, customer_id, address_id)
            if serializer.validated_data.get("is_primary"):
                session.execute(
                    sa.update(CustomerAddress)
                    .where(CustomerAddress.customer_id == customer_id)
                    .values(is_primary=False)
                )
            for key, value in serializer.validated_data.items():
                setattr(address, key, value)
            session.commit()
            session.refresh(address)
            return Response(AddressSerializer(address).data)
        finally:
            session.close()

    def delete(self, request, customer_id, address_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_ADDRESS_WRITE)
        session = SessionLocal()
        try:
            address = self._get_address(session, request, customer_id, address_id)
            session.delete(address)
            session.commit()
            return Response(status=status.HTTP_204_NO_CONTENT)
        finally:
            session.close()


class CustomerPortalAccessView(APIView):
    """Portal access management for a customer.

    GET: Returns portal account info, linked portal users, and the portal URL.
    POST (action=reset): Resets the portal user's password and returns a new temporary credential.
    """

    def get(self, request, customer_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CUSTOMER_READ)
        session = SessionLocal()
        try:
            customer = _get_customer(session, request, customer_id)
            portal_data = self._build_portal_access(session, customer)
            return Response(portal_data)
        finally:
            session.close()

    def post(self, request, customer_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_PORTAL_CREDENTIAL_RESET)

        action = request.data.get("action")
        if action != "reset":
            raise NotFoundError("Only 'reset' action is supported.")

        session = SessionLocal()
        try:
            customer = _get_customer(session, request, customer_id)
            portal_data = self._build_portal_access(session, customer)

            if not portal_data.get("provisioned"):
                raise NotFoundError("No portal account found for this customer.")

            portal_user_id = request.data.get("portal_user_id")
            if not portal_user_id:
                users = portal_data.get("portal_users", [])
                if len(users) == 1:
                    portal_user_id = users[0]["portal_user_id"]
                else:
                    raise NotFoundError("portal_user_id is required when multiple portal users exist.")

            from portal.models import PortalUser
            from portal.services import PortalAuthenticationService

            portal_user = session.get(PortalUser, int(portal_user_id))
            if portal_user is None:
                raise NotFoundError("Portal user not found.")

            temp_password = PortalAuthenticationService.issue_temp_credential(session, portal_user)

            audit.record_audit(
                session,
                actor_user_id=principal.user_id,
                action="portal.credential_reset",
                resource_type="portal_users",
                resource_id=portal_user.portal_user_id,
                description=f"Portal password reset for user {portal_user.email}",
                metadata={"customer_id": customer_id, "portal_user_email": portal_user.email},
                request=request,
            )
            session.commit()

            portal_data["reset_credentials"] = {
                "portal_user_id": portal_user.portal_user_id,
                "email": portal_user.email,
                "temp_password": temp_password,
                "message": "Password has been reset. Share the temporary password securely. The customer must change it on first login.",
            }

            EventBus.publish(
                DomainEvent(
                    event_type="PortalCredentialReset",
                    customer_id=customer_id,
                    source_module="clients",
                    actor_user_id=principal.user_id,
                    actor_type="INTERNAL_USER",
                    summary=f"Portal credentials reset for {portal_user.email}",
                    reference_type="portal_users",
                    reference_id=portal_user.portal_user_id,
                )
            )

            return Response(portal_data)
        finally:
            session.close()

    @staticmethod
    def _build_portal_access(session, customer):
        from portal.models import CustomerAccount, PortalUser, PortalUserCustomer

        portal_url = getattr(settings, "PORTAL_LOGIN_URL", "")
        customer_account = session.execute(
            sa.select(CustomerAccount).where(
                CustomerAccount.customer_id == customer.customer_id,
            )
        ).scalar_one_or_none()

        if customer_account is None:
            return {
                "provisioned": False,
                "portal_url": portal_url,
                "portal_users": [],
            }

        links = session.execute(
            sa.select(PortalUserCustomer).where(
                PortalUserCustomer.customer_account_id == customer_account.customer_account_id,
                PortalUserCustomer.is_active == sa.true(),
            )
        ).scalars().all()

        portal_users = []
        for link in links:
            user = session.get(PortalUser, link.portal_user_id)
            if user is None:
                continue
            portal_users.append({
                "portal_user_id": user.portal_user_id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "status": user.status,
                "role": link.role,
                "is_primary": bool(link.is_primary),
                "last_login_at": user.last_login_at,
            })

        return {
            "provisioned": True,
            "customer_account_id": customer_account.customer_account_id,
            "account_number": customer_account.account_number,
            "account_status": customer_account.status,
            "portal_url": portal_url,
            "portal_users": portal_users,
        }


class CustomerNotificationsView(APIView):
    """Notification history — SMS and email send attempts for a customer.

    Supports filtering by channel (sms, email) and status.
    Sorted newest-first with pagination.
    """

    def get(self, request, customer_id):
        principal = _principal(request)
        _require_permission(principal, PERMISSION_CUSTOMER_READ)
        session = SessionLocal()
        try:
            _get_customer(session, request, customer_id)

            channel = request.query_params.get("channel", "").lower()
            status_filter = request.query_params.get("status", "").upper()

            items = []

            if not channel or channel == "sms":
                if principal.has_permission("communications.sms.read"):
                    sms_stmt = sa.select(
                        sa.literal("sms").label("channel"),
                        SmsMessage.sms_message_id.label("id"),
                        SmsMessage.to_number.label("recipient"),
                        SmsMessage.body.label("content"),
                        SmsMessage.subject.label("subject"),
                        SmsMessage.status.label("delivery_status"),
                        SmsMessage.direction.label("direction"),
                        SmsMessage.sent_at.label("sent_at"),
                        SmsMessage.delivered_at.label("delivered_at"),
                        SmsMessage.created_at.label("created_at"),
                        SmsMessage.failure_reason.label("failure_reason"),
                        SmsMessage.provider_message_id.label("provider_reference"),
                        SmsMessage.provider.label("provider"),
                    ).where(SmsMessage.customer_id == customer_id)

                    if status_filter:
                        sms_stmt = sms_stmt.where(SmsMessage.status == status_filter)

                    for row in session.execute(sms_stmt).all():
                        items.append(dict(row))

            if not channel or channel == "email":
                if principal.has_permission("communications.email.read"):
                    email_stmt = sa.select(
                        sa.literal("email").label("channel"),
                        EmailMessage.email_message_id.label("id"),
                        EmailMessage.to_address.label("recipient"),
                        EmailMessage.body.label("content"),
                        EmailMessage.subject.label("subject"),
                        EmailMessage.status.label("delivery_status"),
                        EmailMessage.direction.label("direction"),
                        EmailMessage.sent_at.label("sent_at"),
                        EmailMessage.delivered_at.label("delivered_at"),
                        EmailMessage.created_at.label("created_at"),
                        EmailMessage.failure_reason.label("failure_reason"),
                        EmailMessage.provider_message_id.label("provider_reference"),
                        EmailMessage.provider.label("provider"),
                    ).where(EmailMessage.customer_id == customer_id)

                    if status_filter:
                        email_stmt = email_stmt.where(EmailMessage.status == status_filter)

                    for row in session.execute(email_stmt).all():
                        items.append(dict(row))

            items.sort(key=lambda i: i.get("sent_at") or i.get("created_at") or _utcnow(), reverse=True)

            total = len(items)

            try:
                page = max(1, int(request.query_params.get("page", 1)))
            except (TypeError, ValueError):
                page = 1
            try:
                page_size = max(1, min(100, int(request.query_params.get("page_size", 20))))
            except (TypeError, ValueError):
                page_size = 20

            start = (page - 1) * page_size
            page_items = items[start:start + page_size]

            results = []
            for item in page_items:
                results.append({
                    "notification_id": item["id"],
                    "channel": item["channel"],
                    "direction": item["direction"],
                    "recipient": item["recipient"],
                    "subject": item.get("subject"),
                    "content_preview": (item.get("content") or "")[:200],
                    "delivery_status": item["delivery_status"],
                    "sent_at": item["sent_at"],
                    "delivered_at": item.get("delivered_at"),
                    "created_at": item["created_at"],
                    "failure_reason": item.get("failure_reason"),
                    "provider_reference": item.get("provider_reference"),
                    "provider": item.get("provider"),
                })

            return Response({
                "count": total,
                "page": page,
                "page_size": page_size,
                "results": results,
            })
        finally:
            session.close()
