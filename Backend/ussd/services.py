import logging
from datetime import datetime, timedelta, timezone

import sqlalchemy as sa

from common.exceptions import NotFoundError
from ussd.enums import (
    USSD_MAIN_MENU,
    USSD_CAMPAIGNS_MENU,
    USSD_REFERRALS_MENU,
    USSD_MOMENTUM_MENU,
    USSD_HELP_MENU,
    USSD_INVALID_INPUT,
    USSD_GOODBYE,
    UssdMenuType,
    UssdSessionStatus,
)
from ussd.models import UssdSession, UssdTransaction, UssdShortCode

logger = logging.getLogger(__name__)

SESSION_TIMEOUT_MINUTES = 5


class UssdSessionService:
    @staticmethod
    def get_or_create_session(db, phone_number: str, session_id: str, text: str = "") -> UssdSession:
        session = db.execute(
            sa.select(UssdSession).where(
                UssdSession.session_id == session_id,
                UssdSession.status == UssdSessionStatus.ACTIVE.value,
            )
        ).scalar_one_or_none()

        if session is None:
            customer_id = UssdSessionService._resolve_customer(db, phone_number)
            session = UssdSession(
                session_id=session_id,
                phone_number=phone_number,
                customer_id=customer_id,
                current_menu=UssdMenuType.MAIN.value,
                status=UssdSessionStatus.ACTIVE.value,
                flow_data={},
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=SESSION_TIMEOUT_MINUTES),
            )
            db.add(session)
            db.flush()
        else:
            if session.expires_at < datetime.now(timezone.utc):
                session.status = UssdSessionStatus.EXPIRED.value
                db.flush()
                return None

        return session

    @staticmethod
    def _resolve_customer(db, phone_number: str):
        from clients.models import Customer
        customer = db.execute(
            sa.select(Customer).where(Customer.phone == phone_number)
        ).scalar_one_or_none()
        return customer.customer_id if customer else None

    @staticmethod
    def advance_session(db, session: UssdSession, user_input: str):
        menu = session.current_menu
        flow_data = session.flow_data or {}

        if menu == UssdMenuType.MAIN.value:
            return UssdMenuHandler.handle_main_menu(db, session, user_input)
        elif menu == UssdMenuType.CAMPAIGNS.value:
            return UssdMenuHandler.handle_campaigns_menu(db, session, user_input)
        elif menu == UssdMenuType.CAMPAIGN_DETAIL.value:
            return UssdMenuHandler.handle_campaign_detail(db, session, user_input)
        elif menu == UssdMenuType.REFERRALS.value:
            return UssdMenuHandler.handle_referrals_menu(db, session, user_input)
        elif menu == UssdMenuType.REFERRAL_SHARE.value:
            return UssdMenuHandler.handle_referral_share(db, session, user_input)
        elif menu == UssdMenuType.MOMENTUM.value:
            return UssdMenuHandler.handle_momentum_menu(db, session, user_input)
        elif menu == UssdMenuType.MOMENTUM_HISTORY.value:
            return UssdMenuHandler.handle_momentum_history(db, session, user_input)
        elif menu == UssdMenuType.HELP.value:
            return UssdMenuHandler.handle_help_menu(db, session, user_input)
        else:
            return UssdMenuHandler.handle_invalid(db, session, user_input)

    @staticmethod
    def log_transaction(db, session_id: str, phone_number: str, customer_id: int,
                       flow_type: str, input_text: str, response_text: str, status: str = "COMPLETED"):
        txn = UssdTransaction(
            session_id=session_id,
            phone_number=phone_number,
            customer_id=customer_id,
            flow_type=flow_type,
            input_text=input_text,
            response_text=response_text,
            status=status,
        )
        db.add(txn)
        db.flush()


class UssdMenuHandler:
    @staticmethod
    def handle_main_menu(db, session, user_input: str):
        if user_input == "1":
            session.current_menu = UssdMenuType.CAMPAIGNS.value
            db.flush()
            return UssdMenuHandler._get_campaigns_list(db)
        elif user_input == "2":
            session.current_menu = UssdMenuType.REFERRALS.value
            db.flush()
            return UssdMenuHandler._get_referrals_menu(db, session)
        elif user_input == "3":
            session.current_menu = UssdMenuType.MOMENTUM.value
            db.flush()
            return UssdMenuHandler._get_momentum_menu(db, session)
        elif user_input == "4":
            session.current_menu = UssdMenuType.HELP.value
            db.flush()
            return USSD_HELP_MENU
        elif user_input == "0":
            session.status = UssdSessionStatus.COMPLETED.value
            db.flush()
            return USSD_GOODBYE
        else:
            return USSD_INVALID_INPUT.format(menu=USSD_MAIN_MENU)

    @staticmethod
    def handle_campaigns_menu(db, session, user_input: str):
        if user_input == "0":
            session.current_menu = UssdMenuType.MAIN.value
            db.flush()
            return USSD_MAIN_MENU

        try:
            index = int(user_input) - 1
            from campaigns.models import Campaign
            campaigns = db.execute(
                sa.select(Campaign).where(Campaign.status == "ACTIVE").order_by(Campaign.campaign_id)
            ).scalars().all()

            if 0 <= index < len(campaigns):
                campaign = campaigns[index]
                session.current_menu = UssdMenuType.CAMPAIGN_DETAIL.value
                session.flow_data = {"campaign_id": campaign.campaign_id}
                db.flush()
                return f"Campaign: {campaign.name}\n{campaign.description or 'No description'}\n1. Join Campaign\n0. Back"
        except (ValueError, IndexError):
            pass

        return USSD_INVALID_INPUT.format(menu=UssdMenuHandler._get_campaigns_list(db))

    @staticmethod
    def handle_campaign_detail(db, session, user_input: str):
        if user_input == "0":
            session.current_menu = UssdMenuType.CAMPAIGNS.value
            db.flush()
            return UssdMenuHandler._get_campaigns_list(db)
        elif user_input == "1":
            campaign_id = (session.flow_data or {}).get("campaign_id")
            if campaign_id and session.customer_id:
                from campaigns.models import Campaign
                campaign = db.get(Campaign, campaign_id)
                if campaign:
                    session.current_menu = UssdMenuType.MAIN.value
                    session.flow_data = {}
                    db.flush()
                    return f"Successfully joined '{campaign.name}'!\n\n{USSD_MAIN_MENU}"

            session.current_menu = UssdMenuType.MAIN.value
            db.flush()
            return f"Unable to join campaign.\n\n{USSD_MAIN_MENU}"

        return USSD_INVALID_INPUT.format(menu="1. Join Campaign\n0. Back")

    @staticmethod
    def handle_referrals_menu(db, session, user_input: str):
        if user_input == "0":
            session.current_menu = UssdMenuType.MAIN.value
            db.flush()
            return USSD_MAIN_MENU
        elif user_input == "1":
            session.current_menu = UssdMenuType.REFERRAL_SHARE.value
            db.flush()
            return UssdMenuHandler._get_referral_share(db, session)
        elif user_input == "2":
            return UssdMenuHandler._get_referral_stats(db, session)

        return USSD_INVALID_INPUT.format(menu=UssdMenuHandler._get_referrals_menu(db, session))

    @staticmethod
    def handle_referral_share(db, session, user_input: str):
        if user_input == "0":
            session.current_menu = UssdMenuType.REFERRALS.value
            db.flush()
            return UssdMenuHandler._get_referrals_menu(db, session)

        return USSD_INVALID_INPUT.format(menu=UssdMenuHandler._get_referral_share(db, session))

    @staticmethod
    def handle_momentum_menu(db, session, user_input: str):
        if user_input == "0":
            session.current_menu = UssdMenuType.MAIN.value
            db.flush()
            return USSD_MAIN_MENU
        elif user_input == "1":
            session.current_menu = UssdMenuType.MOMENTUM_HISTORY.value
            db.flush()
            return UssdMenuHandler._get_momentum_history(db, session)

        return USSD_INVALID_INPUT.format(menu=UssdMenuHandler._get_momentum_menu(db, session))

    @staticmethod
    def handle_momentum_history(db, session, user_input: str):
        if user_input == "0":
            session.current_menu = UssdMenuType.MOMENTUM.value
            db.flush()
            return UssdMenuHandler._get_momentum_menu(db, session)

        return USSD_INVALID_INPUT.format(menu="0. Back")

    @staticmethod
    def handle_help_menu(db, session, user_input: str):
        if user_input == "0":
            session.status = UssdSessionStatus.COMPLETED.value
            db.flush()
            return USSD_GOODBYE

        session.current_menu = UssdMenuType.MAIN.value
        db.flush()
        return USSD_MAIN_MENU

    @staticmethod
    def handle_invalid(db, session, user_input: str):
        session.current_menu = UssdMenuType.MAIN.value
        db.flush()
        return USSD_MAIN_MENU

    @staticmethod
    def _get_campaigns_list(db):
        from campaigns.models import Campaign
        campaigns = db.execute(
            sa.select(Campaign).where(Campaign.status == "ACTIVE").order_by(Campaign.campaign_id).limit(5)
        ).scalars().all()

        if not campaigns:
            return "No active campaigns.\n\n0. Back"

        lines = ["Active Campaigns:"]
        for i, c in enumerate(campaigns, 1):
            lines.append(f"{i}. {c.name}")
        lines.append("0. Back")
        return "\n".join(lines)

    @staticmethod
    def _get_referrals_menu(db, session):
        from referrals.models import ReferralCode
        from referrals.services import ReferralCodeService

        if not session.customer_id:
            return "Please register first.\n\n0. Back"

        rc = db.execute(
            sa.select(ReferralCode).where(
                ReferralCode.referrer_customer_id == session.customer_id,
                ReferralCode.status == "ACTIVE",
            )
        ).scalar_one_or_none()

        if rc is None:
            try:
                rc = ReferralCodeService.create_code(
                    db, session.customer_id, {}, session.customer_id
                )
            except Exception:
                return "Error generating code.\n\n0. Back"

        return f"My Referral Code: {rc.code}\n1. Share Code\n2. View Stats\n0. Back"

    @staticmethod
    def _get_referral_share(db, session):
        from referrals.models import ReferralCode
        rc = db.execute(
            sa.select(ReferralCode).where(
                ReferralCode.referrer_customer_id == session.customer_id,
                ReferralCode.status == "ACTIVE",
            )
        ).scalar_one_or_none()

        if rc:
            return f"Share code: {rc.code}\nDial *900# to join!\n\n0. Back"
        return "No referral code found.\n\n0. Back"

    @staticmethod
    def _get_referral_stats(db, session):
        from referrals.models import ReferralCode
        rc = db.execute(
            sa.select(ReferralCode).where(
                ReferralCode.referrer_customer_id == session.customer_id,
                ReferralCode.status == "ACTIVE",
            )
        ).scalar_one_or_none()

        if rc:
            return f"Code: {rc.code}\nReferrals: {rc.referral_count}\n0. Back"
        return "No referral data.\n\n0. Back"

    @staticmethod
    def _get_momentum_menu(db, session):
        if not session.customer_id:
            return "Please register first.\n\n0. Back"

        from momentum.services import MomentumLedgerService
        balance = MomentumLedgerService.get_balance(db, session.customer_id)
        return f"My Momentum:\nBalance: {balance} points\n1. View History\n0. Back"

    @staticmethod
    def _get_momentum_history(db, session):
        if not session.customer_id:
            return "Please register first.\n\n0. Back"

        from momentum.services import MomentumLedgerService
        entries = MomentumLedgerService.get_ledger_entries(db, session.customer_id, limit=5)

        if not entries:
            return "No history yet.\n\n0. Back"

        lines = ["Recent Activity:"]
        for e in entries:
            sign = "+" if e.entry_type == "EARN" else "-"
            lines.append(f"{sign}{e.points} pts - {e.description or e.source_type}")
        lines.append("0. Back")
        return "\n".join(lines)


class UssdGatewayService:
    SHORT_CODE = "*900#"

    @staticmethod
    def get_short_code_config(db):
        return db.execute(
            sa.select(UssdShortCode).where(UssdShortCode.short_code == UssdGatewayService.SHORT_CODE)
        ).scalar_one_or_none()

    @staticmethod
    def validate_session(db, session_id: str, phone_number: str):
        session = db.execute(
            sa.select(UssdSession).where(
                UssdSession.session_id == session_id,
                UssdSession.phone_number == phone_number,
                UssdSession.status == UssdSessionStatus.ACTIVE.value,
            )
        ).scalar_one_or_none()

        if session and session.expires_at < datetime.now(timezone.utc):
            session.status = UssdSessionStatus.EXPIRED.value
            db.flush()
            return None

        return session
