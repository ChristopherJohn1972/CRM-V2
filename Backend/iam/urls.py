from django.urls import path

from iam.admin_views import (
    MePermissionsView,
    OperatorAccessReviewView,
    OperatorAssignRoleView,
    OperatorDetailView,
    OperatorDirectPermissionView,
    OperatorEffectiveAccessView,
    OperatorEffectiveRightsView,
    OperatorListView,
    OperatorRemoveRoleView,
    OperatorRolesView,
    RightsCatalogueView,
    RightsDetailView,
    RoleDetailView,
    RoleListView,
    RoleOperatorsView,
    RoleRightsView,
    ScopeListView,
)

urlpatterns = [
    # Internal operator/roles administration (single source of truth).
    path("iam/operators", OperatorListView.as_view(), name="iam-operator-list"),
    path("iam/operators/<int:operator_id>", OperatorDetailView.as_view(), name="iam-operator-detail"),
    path("iam/operators/<int:operator_id>/roles", OperatorRolesView.as_view(), name="iam-operator-roles"),
    path(
        "iam/operators/<int:operator_id>/permissions",
        OperatorDirectPermissionView.as_view(),
        name="iam-operator-permissions",
    ),
    path(
        "iam/operators/<int:operator_id>/permissions/<str:permission_code>",
        OperatorDirectPermissionView.as_view(),
        name="iam-operator-permission-detail",
    ),
    path(
        "iam/operators/<int:operator_id>/access-review",
        OperatorAccessReviewView.as_view(),
        name="iam-operator-access-review",
    ),
    path("iam/roles", RoleListView.as_view(), name="iam-role-list"),
    path("iam/roles/<int:role_id>", RoleDetailView.as_view(), name="iam-role-detail"),
    path("iam/roles/<int:role_id>/rights", RoleRightsView.as_view(), name="iam-role-rights"),
    path("iam/roles/<int:role_id>/operators", RoleOperatorsView.as_view(), name="iam-role-operators"),
    path("iam/rights", RightsCatalogueView.as_view(), name="iam-rights-catalogue"),
    path("iam/scopes", ScopeListView.as_view(), name="iam-scope-list"),
]

# Roles & Rights specification surface (section 8 of the backend spec).
# Thin aliases over the same services so a frontend written against the
# /api/rights, /api/roles and /api/operators contracts works identically.
urlpatterns += [
    path("rights", RightsCatalogueView.as_view(), name="rights-catalogue"),
    path("rights/<int:permission_id>", RightsDetailView.as_view(), name="rights-detail"),
    path("roles", RoleListView.as_view(), name="roles-list"),
    path("roles/<int:role_id>", RoleDetailView.as_view(), name="roles-detail"),
    path("roles/<int:role_id>/rights", RoleRightsView.as_view(), name="roles-rights"),
    path("roles/<int:role_id>/operators", RoleOperatorsView.as_view(), name="roles-operators"),
    path("operators/<int:operator_id>/roles", OperatorAssignRoleView.as_view(), name="operators-assign-role"),
    path(
        "operators/<int:operator_id>/roles/<int:role_id>",
        OperatorRemoveRoleView.as_view(),
        name="operators-remove-role",
    ),
    path(
        "operators/<int:operator_id>/effective-rights",
        OperatorEffectiveRightsView.as_view(),
        name="operators-effective-rights",
    ),
    path(
        "operators/<int:operator_id>/effective-access",
        OperatorEffectiveAccessView.as_view(),
        name="operators-effective-access",
    ),
    path("me/permissions", MePermissionsView.as_view(), name="me-permissions"),
]