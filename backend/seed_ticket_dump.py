from __future__ import annotations

import json
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path


DB_PATH = Path("complaints.db")

random.seed(42)


# ============================================================
# EXISTING AGENTS FROM YOUR CURRENT DATABASE
# ============================================================

AGENTS = {
    1: {
        "name": "Alex Morgan",
        "team": "Technical Support",
        "skills": ["technical", "bug", "api", "integration"],
    },
    2: {
        "name": "Priya Nair",
        "team": "Technical Support",
        "skills": ["technical", "workday", "api", "sql"],
    },
    3: {
        "name": "Daniel Chen",
        "team": "Technical Support",
        "skills": ["technical", "infrastructure", "cloud"],
    },
    4: {
        "name": "Meera Shah",
        "team": "Finance Operations",
        "skills": ["billing", "invoice", "payment", "refund"],
    },
    5: {
        "name": "Rohan Das",
        "team": "Fraud Investigation",
        "skills": ["fraud", "transaction", "payment", "investigation"],
    },
    6: {
        "name": "Sara Iyer",
        "team": "Cyber Security",
        "skills": ["security", "breach", "account", "identity"],
    },
    7: {
        "name": "Vikram Rao",
        "team": "Site Reliability",
        "skills": ["outage", "incident", "infrastructure", "availability"],
    },
}


CUSTOMERS = [
    ("John", "Gold"),
    ("Ava", "Gold"),
    ("Smith", "Gold"),
    ("Test Customer", "Standard"),
    ("Michael", "Silver"),
    ("Emily", "Gold"),
    ("Rahul", "Standard"),
    ("Priyanka", "Gold"),
    ("Daniel", "Silver"),
    ("Sophia", "Gold"),
]


# ============================================================
# ISSUE CATALOG
#
# Multiple variants per issue create meaningful semantic
# clusters for hybrid retrieval.
# ============================================================

ISSUES = [

    # --------------------------------------------------------
    # SECURITY
    # --------------------------------------------------------

    {
        "category": "Security",
        "subcategory": "Account Compromise",
        "team": "Cyber Security",
        "queue": "SECURITY-L1",
        "priority": "Critical",
        "sla": 4,
        "first_response": 15,
        "business_impact": "High",
        "routing_reason": "Urgent Security Issue",
        "customer_intent": "Report Security Issue",
        "templates": [
            (
                "I received suspicious login alerts from {location}. "
                "I did not initiate these sign-ins and I believe my "
                "credentials may have been compromised."
            ),
            (
                "There are multiple unfamiliar login attempts on my account "
                "from {location}. Please investigate whether someone has "
                "gained unauthorized access."
            ),
            (
                "My account is showing login activity from a foreign country. "
                "I am concerned that my credentials have been stolen."
            ),
            (
                "I received several authentication alerts for sign-ins "
                "I do not recognize. I need the account secured immediately."
            ),
        ],
        "keywords": ["security", "login", "credential", "account", "compromise"],
    },

    {
        "category": "Security",
        "subcategory": "MFA Issue",
        "team": "Cyber Security",
        "queue": "SECURITY-L1",
        "priority": "High",
        "sla": 8,
        "first_response": 30,
        "business_impact": "High",
        "routing_reason": "Security Authentication Issue",
        "customer_intent": "Restore Access",
        "templates": [
            "MFA codes are not arriving and I cannot complete the sign-in.",
            "The authenticator is rejecting valid verification codes.",
            "Two-factor authentication is failing even though the credentials are correct.",
            "I am locked out because the second authentication factor is not working.",
        ],
        "keywords": ["mfa", "authentication", "verification", "security"],
    },

    {
        "category": "Data Privacy",
        "subcategory": "Unauthorized Access",
        "team": "Cyber Security",
        "queue": "SECURITY-L1",
        "priority": "Critical",
        "sla": 4,
        "first_response": 15,
        "business_impact": "High",
        "routing_reason": "Sensitive customer data exposure",
        "customer_intent": "Report Privacy Issue",
        "templates": [
            (
                "I can see another customer's personal information in my "
                "dashboard. This appears to be a serious privacy problem."
            ),
            (
                "The dashboard is displaying information belonging to a different "
                "customer account."
            ),
            (
                "I can access records that should belong to another customer. "
                "Please investigate the access-control issue immediately."
            ),
        ],
        "keywords": ["privacy", "data exposure", "unauthorized access", "pii"],
    },

    # --------------------------------------------------------
    # ACCOUNT ACCESS
    # --------------------------------------------------------

    {
        "category": "Account Access",
        "subcategory": "Login Issue",
        "team": "Technical Support",
        "queue": "GENERAL-L1",
        "priority": "Medium",
        "sla": 24,
        "first_response": 60,
        "business_impact": "Medium",
        "routing_reason": "Technical Support",
        "customer_intent": "Resolve Issue",
        "templates": [
            "I have been locked out of my account after several failed sign-in attempts.",
            "My account is locked and I cannot log in even with the correct password.",
            "I am unable to access the portal because my account has been locked.",
            "The login page keeps rejecting my credentials and my account now appears locked.",
        ],
        "keywords": ["account access", "locked", "login", "credentials"],
    },

    {
        "category": "Account Access",
        "subcategory": "Password Reset",
        "team": "Technical Support",
        "queue": "GENERAL-L1",
        "priority": "Medium",
        "sla": 24,
        "first_response": 60,
        "business_impact": "Medium",
        "routing_reason": "Technical Support",
        "customer_intent": "Reset Password",
        "templates": [
            "I forgot my password and the verification email is not arriving.",
            "The password reset link is not being delivered to my email address.",
            "I requested a password reset several times but no email has arrived.",
            "I cannot complete the password reset because the verification message never arrives.",
        ],
        "keywords": ["password", "reset", "verification email", "login"],
    },

    {
        "category": "Account Access",
        "subcategory": "Permission Change",
        "team": "Technical Support",
        "queue": "GENERAL-L1",
        "priority": "Low",
        "sla": 48,
        "first_response": 120,
        "business_impact": "Medium",
        "routing_reason": "Needs account permission update by admin",
        "customer_intent": "Request Access Change",
        "templates": [
            "I need my employee account changed to a supervisor role.",
            "Please change my access level because I have taken on a new role.",
            "My current permissions are insufficient for my responsibilities.",
            "I need an administrative access change for my new responsibilities.",
        ],
        "keywords": ["access", "role", "permission", "account"],
    },

    # --------------------------------------------------------
    # TECHNICAL
    # --------------------------------------------------------

    {
        "category": "Technical",
        "subcategory": "Mobile Application Issue",
        "team": "Technical Support",
        "queue": "TECH-L1",
        "priority": "High",
        "sla": 8,
        "first_response": 30,
        "business_impact": "Medium",
        "routing_reason": "Technical Support Required",
        "customer_intent": "Troubleshooting",
        "templates": [
            "The mobile application crashes whenever I upload a document.",
            "The app closes unexpectedly every time I try to attach a file.",
            "Uploading a document consistently causes the mobile application to crash.",
            "The application becomes unresponsive when I submit an attachment.",
        ],
        "keywords": ["mobile", "crash", "upload", "document", "application"],
    },

    {
        "category": "Technical",
        "subcategory": "Internet Connectivity",
        "team": "Technical Support",
        "queue": "TECH-L1",
        "priority": "Medium",
        "sla": 24,
        "first_response": 60,
        "business_impact": "Medium",
        "routing_reason": "Technical Support",
        "customer_intent": "Troubleshooting",
        "templates": [
            "I am unable to connect to the internet through the application.",
            "The service keeps timing out when I try to connect.",
            "Connectivity drops repeatedly while I am using the platform.",
            "The application cannot maintain a stable connection to the service.",
        ],
        "keywords": ["internet", "connectivity", "connection", "timeout"],
    },

    {
        "category": "Technical",
        "subcategory": "API Integration",
        "team": "Technical Support",
        "queue": "TECH-L2",
        "priority": "High",
        "sla": 8,
        "first_response": 30,
        "business_impact": "High",
        "routing_reason": "API Integration Failure",
        "customer_intent": "Resolve Integration Issue",
        "templates": [
            "Our integration API is returning 500 errors when submitting employee data.",
            "The downstream API integration has started failing after working normally.",
            "Requests sent through the integration endpoint are timing out intermittently.",
            "The API integration is returning authentication and processing errors.",
        ],
        "keywords": ["api", "integration", "500", "timeout", "endpoint"],
    },

    {
        "category": "Technical",
        "subcategory": "Service Outage",
        "team": "Site Reliability",
        "queue": "SRE-L1",
        "priority": "Critical",
        "sla": 4,
        "first_response": 15,
        "business_impact": "High",
        "routing_reason": "Critical Service Outage",
        "customer_intent": "Report Outage",
        "templates": [
            "The portal is unavailable for our entire organization.",
            "All employees are unable to access the service right now.",
            "The website has been down for more than an hour.",
            "Our production users cannot reach the service and business operations are affected.",
        ],
        "keywords": ["outage", "availability", "portal", "down", "service"],
    },

    {
        "category": "Technical",
        "subcategory": "Payroll Processing",
        "team": "Technical Support",
        "queue": "TECH-L2",
        "priority": "Critical",
        "sla": 4,
        "first_response": 15,
        "business_impact": "High",
        "routing_reason": "Critical Technical Issue",
        "customer_intent": "Resolve Business-Critical Issue",
        "templates": [
            "Payroll processing has stopped and salaries cannot be generated.",
            "The payroll run is failing and hundreds of employees are affected.",
            "We cannot complete payroll processing before the scheduled pay cycle.",
            "Payroll calculation has stopped across the organization.",
        ],
        "keywords": ["payroll", "processing", "salary", "employees", "business critical"],
    },

    # --------------------------------------------------------
    # FINANCE
    # --------------------------------------------------------

    {
        "category": "Billing",
        "subcategory": "Duplicate Charge",
        "team": "Finance Operations",
        "queue": "BILLING-L1",
        "priority": "High",
        "sla": 8,
        "first_response": 30,
        "business_impact": "Medium",
        "routing_reason": "Billing Dispute",
        "customer_intent": "Request Refund",
        "templates": [
            "I was charged twice for the same subscription this month.",
            "The same invoice amount appears twice on my statement.",
            "I see a duplicate payment for one subscription and need the extra charge refunded.",
            "Two identical charges were processed for the same billing period.",
        ],
        "keywords": ["billing", "duplicate", "charge", "payment", "refund"],
    },

    {
        "category": "Subscription",
        "subcategory": "Activation Issue",
        "team": "Finance Operations",
        "queue": "BILLING-L1",
        "priority": "Medium",
        "sla": 24,
        "first_response": 60,
        "business_impact": "Medium",
        "routing_reason": "Payment and Subscription Activation",
        "customer_intent": "Resolve Subscription Issue",
        "templates": [
            "I paid for the premium plan but the service is still not activated.",
            "Payment succeeded but my new subscription remains inactive.",
            "The subscription payment was completed but premium features are unavailable.",
            "The charge was successful but the account is still on the previous plan.",
        ],
        "keywords": ["subscription", "activation", "payment", "premium"],
    },

    {
        "category": "Billing",
        "subcategory": "Refund Request",
        "team": "Finance Operations",
        "queue": "BILLING-L1",
        "priority": "Medium",
        "sla": 24,
        "first_response": 60,
        "business_impact": "Medium",
        "routing_reason": "Finance Operations",
        "customer_intent": "Request Refund",
        "templates": [
            "I need a refund for a payment that should not have been processed.",
            "Please review this charge and process a refund if eligible.",
            "A refund is required because the service was not delivered as expected.",
            "I would like to request a refund for the recent transaction.",
        ],
        "keywords": ["refund", "payment", "charge", "finance"],
    },

    # --------------------------------------------------------
    # FRAUD
    # --------------------------------------------------------

    {
        "category": "Fraud",
        "subcategory": "Unauthorized Transaction",
        "team": "Fraud Investigation",
        "queue": "FRAUD-L1",
        "priority": "Critical",
        "sla": 4,
        "first_response": 15,
        "business_impact": "High",
        "routing_reason": "Security Incident",
        "customer_intent": "Report Fraud",
        "templates": [
            "An unauthorized payment was made from my account.",
            "I do not recognize a transaction that was processed yesterday.",
            "Someone used my account to make a payment that I did not authorize.",
            "There is a suspicious transaction on my statement that I want investigated.",
        ],
        "keywords": ["fraud", "unauthorized", "transaction", "payment", "investigation"],
    },

    {
        "category": "Fraud",
        "subcategory": "Suspicious Transaction",
        "team": "Fraud Investigation",
        "queue": "FRAUD-L1",
        "priority": "High",
        "sla": 8,
        "first_response": 30,
        "business_impact": "High",
        "routing_reason": "Potential Fraud Investigation",
        "customer_intent": "Report Suspicious Activity",
        "templates": [
            "There is a transaction on my account that looks suspicious.",
            "I noticed a payment I do not recognize and want it reviewed.",
            "A recent transaction appears unusual and may be fraudulent.",
            "Please investigate a potentially unauthorized payment.",
        ],
        "keywords": ["fraud", "transaction", "suspicious", "payment"],
    },

    # --------------------------------------------------------
    # CUSTOMER SERVICE
    # --------------------------------------------------------

    {
        "category": "Customer Service",
        "subcategory": "Lack of Response",
        "team": "Technical Support",
        "queue": "GENERAL-L1",
        "priority": "High",
        "sla": 8,
        "first_response": 30,
        "business_impact": "High",
        "routing_reason": "Escalation to Supervisor",
        "customer_intent": "Escalation",
        "templates": [
            "I have already raised multiple tickets and nobody has responded.",
            "This is my third follow-up and I still have no response.",
            "The previous support request has been ignored and I need immediate attention.",
            "I have been waiting for an update for several days with no response.",
        ],
        "keywords": ["support", "response", "follow-up", "escalation"],
    },

]


# ============================================================
# SMALL HELPERS
# ============================================================

def clamp(value, low=0, high=100):
    return max(low, min(high, value))


def sentiment_for_priority(priority):
    if priority == "Critical":
        return random.choice(["Negative", "Negative", "Fear"])
    if priority == "High":
        return random.choice(["Negative", "Negative", "Frustrated"])
    if priority == "Medium":
        return random.choice(["Negative", "Neutral", "Frustration"])
    return random.choice(["Neutral", "Positive"])


def emotion_for_category(category):
    mapping = {
        "Security": ["Fear", "Urgency"],
        "Data Privacy": ["Fear", "Urgency"],
        "Fraud": ["Urgency", "Fear"],
        "Technical": ["Frustration", "Urgency"],
        "Account Access": ["Frustration", "Confusion"],
        "Billing": ["Frustration", "Concern"],
        "Subscription": ["Frustration", "Concern"],
        "Customer Service": ["Frustration", "Dissatisfaction"],
    }
    return random.choice(mapping.get(category, ["Frustration", "Concern"]))


def make_location():
    return random.choice(
        [
            "Germany",
            "Singapore",
            "United Kingdom",
            "Brazil",
            "Canada",
            "Australia",
            "the United States",
        ]
    )


def make_text(issue):
    template = random.choice(issue["templates"])

    return template.format(
        location=make_location()
    )


def make_summary(issue, text):
    base = issue["templates"][0]
    if "{location}" in base:
        base = base.replace("{location}", "a foreign location")

    summary = base.rstrip(".!?")

    if len(summary) > 115:
        summary = summary[:112] + "..."

    return summary


def priority_score(priority):
    return {
        "Critical": 90,
        "High": random.choice([60, 65, 70, 75]),
        "Medium": random.choice([40, 45, 50, 55]),
        "Low": random.choice([20, 25, 30]),
    }[priority]


def random_created_at(
    now: datetime,
    days_back_min: int,
    days_back_max: int,
):
    days_back = random.randint(
        days_back_min,
        days_back_max,
    )

    hour = random.randint(7, 18)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)

    dt = now - timedelta(days=days_back)

    return dt.replace(
        hour=hour,
        minute=minute,
        second=second,
        microsecond=random.randint(0, 999999),
    )


def choose_agent(team, ticket_index):
    candidates = [
        agent_id
        for agent_id, agent in AGENTS.items()
        if agent["team"] == team
    ]

    if not candidates:
        return None

    return candidates[
        ticket_index % len(candidates)
    ]


def resolution_text(issue):
    category = issue["category"]

    if category in {"Security", "Data Privacy"}:
        return random.choice(
            [
                "Identity was verified, suspicious sessions were revoked, "
                "credentials were reset and the access-control condition was validated.",
                "The security team reviewed authentication activity, invalidated "
                "suspicious sessions and confirmed that unauthorized access was removed.",
            ]
        )

    if category == "Fraud":
        return random.choice(
            [
                "The transaction was investigated, account security was restored "
                "and the disputed payment was escalated through the fraud process.",
                "Fraud operations reviewed the transaction history, secured the account "
                "and completed the appropriate dispute workflow.",
            ]
        )

    if category in {"Billing", "Subscription"}:
        return random.choice(
            [
                "Billing records were reconciled, the affected transaction was corrected "
                "and the customer was informed of the outcome.",
                "Finance operations reviewed the payment, corrected the subscription state "
                "and confirmed the billing adjustment.",
            ]
        )

    if category == "Technical":
        return random.choice(
            [
                "The resolver reproduced the issue, identified the configuration or "
                "service condition, applied the corrective action and validated recovery.",
                "Technical support reproduced the reported behavior, applied the approved "
                "remediation and confirmed successful validation with the customer.",
            ]
        )

    return random.choice(
        [
            "The issue was investigated, the appropriate operational action was completed "
            "and the customer confirmed the expected outcome.",
            "The support team reviewed the case, completed the required action and verified "
            "that the customer could continue normal operations.",
        ]
    )


def main():
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found: {DB_PATH.resolve()}"
        )

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    now = datetime.now()

    existing_max_id = conn.execute(
        "SELECT COALESCE(MAX(id), 0) FROM complaints"
    ).fetchone()[0]

    next_ticket_id = existing_max_id + 1

    # --------------------------------------------------------
    # Distribution
    # --------------------------------------------------------

    counts = {
        "RESOLVED": 210,
        "CLOSED": 35,
        "IN_PROGRESS": 20,
        "OPEN_ASSIGNED": 25,
        "OPEN_UNASSIGNED": 10,
    }

    issue_pool = []

    for issue in ISSUES:
        issue_pool.extend(
            [issue] * 8
        )

    random.shuffle(issue_pool)

    generated = []

    # --------------------------------------------------------
    # Generate
    # --------------------------------------------------------

    for index in range(sum(counts.values())):

        if index < counts["RESOLVED"]:
            lifecycle = "RESOLVED"
            created = random_created_at(
                now,
                45,
                420,
            )

        elif index < (
            counts["RESOLVED"]
            + counts["CLOSED"]
        ):
            lifecycle = "CLOSED"
            created = random_created_at(
                now,
                45,
                420,
            )

        elif index < (
            counts["RESOLVED"]
            + counts["CLOSED"]
            + counts["IN_PROGRESS"]
        ):
            lifecycle = "IN_PROGRESS"
            created = random_created_at(
                now,
                0,
                15,
            )

        elif index < (
            counts["RESOLVED"]
            + counts["CLOSED"]
            + counts["IN_PROGRESS"]
            + counts["OPEN_ASSIGNED"]
        ):
            lifecycle = "OPEN_ASSIGNED"
            created = random_created_at(
                now,
                0,
                12,
            )

        else:
            lifecycle = "OPEN_UNASSIGNED"
            created = random_created_at(
                now,
                0,
                10,
            )

        issue = issue_pool[
            index % len(issue_pool)
        ]

        # Introduce extra randomization without
        # destroying cluster structure.
        issue = random.choice(
            [
                issue,
                issue,
                issue,
            ]
        )

        customer_name, customer_tier = random.choice(
            CUSTOMERS
        )

        complaint = make_text(issue)

        priority = issue["priority"]
        pscore = priority_score(
            priority
        )

        category = issue["category"]
        team = issue["team"]

        assigned_agent_id = None
        assigned_agent_name = None

        if lifecycle in {
            "RESOLVED",
            "CLOSED",
            "IN_PROGRESS",
            "OPEN_ASSIGNED",
        }:
            assigned_agent_id = choose_agent(
                team,
                index,
            )

            if assigned_agent_id:
                assigned_agent_name = AGENTS[
                    assigned_agent_id
                ]["name"]

        # ----------------------------------------------------
        # SLA
        # ----------------------------------------------------

        sla_hours = issue["sla"]

        sla_deadline = (
            created
            + timedelta(
                hours=sla_hours
            )
        )

        first_response_deadline = (
            created
            + timedelta(
                minutes=issue[
                    "first_response"
                ]
            )
        )

        first_response_at = None
        resolved_at = None
        updated_at = created

        if lifecycle in {
            "RESOLVED",
            "CLOSED",
            "IN_PROGRESS",
        }:

            response_delay_minutes = random.randint(
                max(5, issue["first_response"] // 3),
                max(
                    issue["first_response"] + 15,
                    issue["first_response"] * 2,
                ),
            )

            first_response_at = (
                created
                + timedelta(
                    minutes=response_delay_minutes
                )
            )

            if lifecycle in {
                "RESOLVED",
                "CLOSED",
            }:

                resolution_hours = random.randint(
                    max(1, sla_hours // 2),
                    max(
                        2,
                        sla_hours + 4,
                    ),
                )

                resolved_at = (
                    created
                    + timedelta(
                        hours=resolution_hours,
                    )
                )

                updated_at = resolved_at

            else:
                updated_at = first_response_at

        # ----------------------------------------------------
        # Deliberately make a small proportion of historical
        # cases SLA-breached, so the retrieval corpus includes
        # both successful and problematic cases.
        # ----------------------------------------------------

        breach = (
            lifecycle in {
                "RESOLVED",
                "CLOSED",
            }
            and random.random() < 0.18
        )

        if breach and resolved_at:
            sla_deadline = (
                resolved_at
                - timedelta(
                    hours=random.randint(1, 8)
                )
            )

        escalation_required = (
            priority in {
                "Critical",
                "High",
            }
            and random.random() < 0.55
        )

        escalation_level = (
            random.choice([1, 2])
            if escalation_required
            else 0
        )

        escalation_reason = (
            "Priority and/or SLA exposure required elevated operational attention."
            if escalation_required
            else None
        )

        escalation_owner = (
            "OPERATIONS_MANAGER"
            if escalation_required
            else None
        )

        escalated_at = (
            created + timedelta(
                hours=random.randint(1, 12)
            )
            if escalation_required
            else None
        )

        escalation_count = (
            random.randint(1, 2)
            if escalation_required
            else 0
        )

        # ----------------------------------------------------
        # Assignment explanation
        # ----------------------------------------------------

        if assigned_agent_name:
            if lifecycle in {
                "RESOLVED",
                "CLOSED",
            }:
                assignment_explanation = (
                    f"Historical routing assigned to "
                    f"{assigned_agent_name} based on "
                    f"team alignment, skills, workload and experience."
                )
            else:
                assignment_explanation = (
                    f"Auto-assigned to "
                    f"{assigned_agent_name} using normal routing."
                )
        else:
            assignment_explanation = (
                "No eligible resolver was available at creation time."
            )

        status = (
            "OPEN"
            if lifecycle == "OPEN_ASSIGNED"
            or lifecycle == "OPEN_UNASSIGNED"
            else lifecycle
        )

        # ----------------------------------------------------
        # Insert complaint
        # ----------------------------------------------------

        conn.execute(
            """
            INSERT INTO complaints (
                id,
                customer_name,
                customer_tier,
                complaint_text,
                category,
                subcategory,
                sentiment,
                emotion,
                business_impact,
                customer_intent,
                summary,
                confidence,
                priority_score,
                priority_level,
                assigned_team,
                queue,
                escalation_required,
                sla_hours,
                routing_reason,
                status,
                created_at,
                keywords,
                priority_source,
                assigned_agent_id,
                assigned_agent_name,
                sla_deadline,
                first_response_at,
                resolved_at,
                assignment_score,
                assignment_explanation,
                updated_at,
                first_response_sla_minutes,
                first_response_deadline,
                sla_paused_at,
                sla_total_paused_seconds,
                escalation_level,
                escalated_at,
                escalation_reason,
                escalation_owner,
                escalation_count
            )
            VALUES (
                ?,?,?,?,?,?,?,?,?,?,
                ?,?,?,?,?,?,?,?,?,?,
                ?,?,?,?,?,?,?,?,?,?,
                ?,?,?,?,?,?,?,?,?,?
            )
            """,
            (
                next_ticket_id,
                customer_name,
                customer_tier,
                complaint,
                category,
                issue["subcategory"],
                sentiment_for_priority(priority),
                emotion_for_category(category),
                issue["business_impact"],
                issue["customer_intent"],
                make_summary(issue, complaint),
                round(
                    random.uniform(0.88, 0.99),
                    2,
                ),
                pscore,
                priority,
                team,
                issue["queue"],
                int(escalation_required),
                sla_hours,
                issue["routing_reason"],
                status,
                created.isoformat(sep=" "),
                json.dumps(
                    issue["keywords"]
                ),
                "AI",
                assigned_agent_id,
                assigned_agent_name,
                sla_deadline.isoformat(sep=" "),
                first_response_at.isoformat(sep=" ")
                if first_response_at
                else None,
                resolved_at.isoformat(sep=" ")
                if resolved_at
                else None,
                round(
                    random.uniform(72, 99),
                    2,
                )
                if assigned_agent_id
                else None,
                assignment_explanation
                if assigned_agent_id
                else None,
                updated_at.isoformat(sep=" "),
                issue["first_response"],
                first_response_deadline.isoformat(
                    sep=" "
                ),
                None,
                0,
                escalation_level,
                escalated_at.isoformat(sep=" ")
                if escalated_at
                else None,
                escalation_reason,
                escalation_owner,
                escalation_count,
            ),
        )

        # ----------------------------------------------------
        # Ticket events
        # ----------------------------------------------------

        conn.execute(
            """
            INSERT INTO ticket_events (
                ticket_id,
                actor_id,
                actor_role,
                event_type,
                from_value,
                to_value,
                notes,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                next_ticket_id,
                None,
                None,
                "CREATED",
                None,
                "OPEN",
                "Historical ticket seeded for retrieval corpus.",
                created.isoformat(sep=" "),
            ),
        )

        if assigned_agent_name:

            conn.execute(
                """
                INSERT INTO ticket_events (
                    ticket_id,
                    actor_id,
                    actor_role,
                    event_type,
                    from_value,
                    to_value,
                    notes,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    next_ticket_id,
                    None,
                    None,
                    "AUTO_ASSIGNED",
                    None,
                    assigned_agent_name,
                    assignment_explanation,
                    (
                        created
                        + timedelta(
                            minutes=2
                        )
                    ).isoformat(sep=" "),
                ),
            )

        if lifecycle == "IN_PROGRESS":

            conn.execute(
                """
                INSERT INTO ticket_events (
                    ticket_id,
                    actor_id,
                    actor_role,
                    event_type,
                    from_value,
                    to_value,
                    notes,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    next_ticket_id,
                    assigned_agent_id,
                    "agent",
                    "STATUS_CHANGED",
                    "OPEN",
                    "IN_PROGRESS",
                    "Resolver started work.",
                    updated_at.isoformat(sep=" "),
                ),
            )

        if lifecycle in {
            "RESOLVED",
            "CLOSED",
        }:

            resolution = resolution_text(issue)

            conn.execute(
                """
                INSERT INTO ticket_events (
                    ticket_id,
                    actor_id,
                    actor_role,
                    event_type,
                    from_value,
                    to_value,
                    notes,
                    created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    next_ticket_id,
                    assigned_agent_id,
                    "agent",
                    "RESOLVED",
                    "IN_PROGRESS",
                    "RESOLVED",
                    resolution,
                    (
                        resolved_at
                        or updated_at
                    ).isoformat(sep=" "),
                ),
            )

            if lifecycle == "CLOSED":

                conn.execute(
                    """
                    INSERT INTO ticket_events (
                        ticket_id,
                        actor_id,
                        actor_role,
                        event_type,
                        from_value,
                        to_value,
                        notes,
                        created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        next_ticket_id,
                        assigned_agent_id,
                        "agent",
                        "CLOSED",
                        "RESOLVED",
                        "CLOSED",
                        "Historical ticket closed after resolution.",
                        (
                            resolved_at
                            + timedelta(
                                hours=random.randint(2, 72)
                            )
                        ).isoformat(sep=" "),
                    ),
                )

        generated.append(
            {
                "id": next_ticket_id,
                "status": status,
                "priority": priority,
                "category": category,
                "team": team,
                "assigned_agent": assigned_agent_name,
            }
        )

        next_ticket_id += 1

    conn.commit()

    # --------------------------------------------------------
    # Summary
    # --------------------------------------------------------

    total = conn.execute(
        "SELECT COUNT(*) FROM complaints"
    ).fetchone()[0]

    resolved = conn.execute(
        """
        SELECT COUNT(*)
        FROM complaints
        WHERE status IN ('RESOLVED', 'CLOSED')
        """
    ).fetchone()[0]

    active = conn.execute(
        """
        SELECT COUNT(*)
        FROM complaints
        WHERE status IN ('OPEN', 'IN_PROGRESS', 'PENDING_CUSTOMER')
        """
    ).fetchone()[0]

    unassigned = conn.execute(
        """
        SELECT COUNT(*)
        FROM complaints
        WHERE assigned_agent_id IS NULL
          AND status IN ('OPEN', 'IN_PROGRESS', 'PENDING_CUSTOMER')
        """
    ).fetchone()[0]

    print("=" * 70)
    print("TICKET DUMP SEED COMPLETED")
    print("=" * 70)
    print(f"Added tickets        : {len(generated)}")
    print(f"Total tickets        : {total}")
    print(f"Historical resolved  : {resolved}")
    print(f"Active tickets       : {active}")
    print(f"Unassigned active    : {unassigned}")
    print()
    print("Retrieval corpus is now large enough for:")
    print("  - semantic similarity")
    print("  - hybrid dense/sparse retrieval")
    print("  - RRF fusion")
    print("  - cross-encoder reranking")
    print("  - historical precedent retrieval")
    print()
    print(
        "IMPORTANT: rebuild your resolution index after seeding:"
    )
    print(
        "python rebuild_resolution_index.py"
    )
    print("=" * 70)

    conn.close()


if __name__ == "__main__":
    main()