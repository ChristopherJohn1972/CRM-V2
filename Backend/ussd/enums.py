from enum import Enum


class UssdSessionStatus(str, Enum):
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"
    FAILED = "FAILED"


class UssdMenuType(str, Enum):
    MAIN = "MAIN"
    CAMPAIGNS = "CAMPAIGNS"
    CAMPAIGN_DETAIL = "CAMPAIGN_DETAIL"
    REFERRALS = "REFERRALS"
    REFERRAL_SHARE = "REFERRAL_SHARE"
    MOMENTUM = "MOMENTUM"
    MOMENTUM_HISTORY = "MOMENTUM_HISTORY"
    HELP = "HELP"
    INVALID = "INVALID"


class UssdFlowType(str, Enum):
    CAMPAIGN_LIST = "CAMPAIGN_LIST"
    CAMPAIGN_JOIN = "CAMPAIGN_JOIN"
    REFERRAL_GENERATE = "REFERRAL_GENERATE"
    REFERRAL_TRACK = "REFERRAL_TRACK"
    MOMENTUM_BALANCE = "MOMENTUM_BALANCE"
    MOMENTUM_HISTORY = "MOMENTUM_HISTORY"


USSD_MAIN_MENU = """Welcome to CRM *900#
1. View Campaigns
2. My Referrals
3. My Momentum
4. Help
0. Exit"""

USSD_CAMPAIGNS_MENU = """Active Campaigns:
{campaigns}
0. Back"""

USSD_REFERRALS_MENU = """My Referrals:
{referral_code}
1. Share Code
2. View Stats
0. Back"""

USSD_MOMENTUM_MENU = """My Momentum:
Balance: {balance} points
1. View History
0. Back"""

USSD_HELP_MENU = """Help:
*900# - CRM Short Code
1. Campaigns - View active promotions
2. Referrals - Share & earn rewards
3. Momentum - Check your points
0. Exit"""

USSD_INVALID_INPUT = """Invalid input. Please try again.
{menu}"""

USSD_SESSION_TIMEOUT = """Session timed out. Please dial *900# again."""

USSD_GOODBYE = """Thank you for using *900#
Goodbye!"""
