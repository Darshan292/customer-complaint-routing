from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.services.team_service import TeamService

from app.models.agent import Agent
from app.models.complaint import Complaint

from app.services.workforce_service import WorkforceService


@dataclass
class AssignmentCandidate:
    agent: Agent
    score: float
    workload: float
    utilization: float
    skill_score: float
    capacity_score: float
    priority_load_score: float
    experience_score: float
    sla_risk_score: float
    reasons: list[str]


class AssignmentService:
    """
    Enterprise ticket assignment engine.

    Assignment is based on:
      - team eligibility
      - active status
      - effective workload
      - resolver capacity
      - skill/category match
      - experience
      - priority distribution
      - SLA exposure
    """

    # Severity affects workload much more than a simple ticket count.
    PRIORITY_WEIGHTS = {
        "Low": 0.5,
        "Medium": 1.0,
        "High": 1.75,
        "Critical": 3.0,
    }

    STATUS_MULTIPLIERS = {
        "OPEN": 1.0,
        "IN_PROGRESS": 1.25,
        "PENDING_CUSTOMER": 0.35,
    }

    # Maximum number of tickets above which capacity pressure becomes extreme.
    MAX_UTILIZATION = 1.25

    
    @classmethod
    def _get_active_tickets(
        cls,
        db: Session,
        agent_id: int,
    ) -> list[Complaint]:
        return (
            db.query(Complaint)
            .filter(
                Complaint.assigned_agent_id == agent_id,
                Complaint.status.in_(
                    [
                        "OPEN",
                        "IN_PROGRESS",
                        "PENDING_CUSTOMER",
                    ]
                ),
            )
            .all()
        )

    @classmethod
    def _calculate_workload(
        cls,
        tickets: list[Complaint],
    ) -> float:
        """
        Converts raw tickets into effective workload.

        Example:

        1 Critical + 2 Low
        = 3.0 + 0.5 + 0.5
        = 4.0 effective workload.
        """

        workload = 0.0

        for ticket in tickets:
            priority_weight = cls.PRIORITY_WEIGHTS.get(
                ticket.priority_level,
                1.0,
            )

            status_multiplier = cls.STATUS_MULTIPLIERS.get(
                ticket.status,
                1.0,
            )

            workload += priority_weight * status_multiplier

        return workload

    @classmethod
    def _skill_match(
        cls,
        agent: Agent,
        category: Optional[str],
        subcategory: Optional[str],
    ) -> tuple[float, list[str]]:

        raw_skills = [
            skill.strip().lower()
            for skill in (agent.skills or "").split(",")
            if skill.strip()
        ]

        target_terms = set()

        if category:
            target_terms.add(category.strip().lower())

        if subcategory:
            target_terms.add(subcategory.strip().lower())

        if not target_terms:
            return 0.0, ["No category/subcategory available"]

        matched = [
            skill
            for skill in raw_skills
            if any(
                skill in target
                or target in skill
                for target in target_terms
            )
        ]

        if not matched:
            return 0.0, ["No direct skill match"]

        # 0 - 100
        score = min(len(matched) / max(len(target_terms), 1), 1.0) * 100

        return score, [
            f"Matched skills: {', '.join(matched)}"
        ]

    @classmethod
    def _capacity_score(
        cls,
        workload: float,
        capacity: int,
    ) -> tuple[float, float]:

        effective_capacity = max(float(capacity or 1), 1.0)

        utilization = workload / effective_capacity

        # Best candidate is someone with the most headroom.
        score = max(
            0.0,
            100.0 * (1.0 - min(utilization, 1.0)),
        )

        return score, utilization

    @classmethod
    def _priority_load_score(
        cls,
        tickets: list[Complaint],
    ) -> float:

        if not tickets:
            return 100.0

        weighted_load = sum(
            cls.PRIORITY_WEIGHTS.get(
                ticket.priority_level,
                1.0,
            )
            for ticket in tickets
        )

        critical_count = sum(
            ticket.priority_level == "Critical"
            for ticket in tickets
        )

        high_count = sum(
            ticket.priority_level == "High"
            for ticket in tickets
        )

        score = 100.0

        score -= min(weighted_load * 8, 60)

        # Protect agents already handling severe incidents.
        score -= min(critical_count * 15, 30)
        score -= min(high_count * 5, 15)

        return max(score, 0.0)

    @classmethod
    def _experience_score(
        cls,
        experience_years: float,
    ) -> float:

        # Cap experience contribution at 10 years.
        capped = min(max(experience_years or 0.0, 0.0), 10.0)

        return capped / 10.0 * 100.0

    @classmethod
    def _sla_risk_score(
        cls,
        tickets: list[Complaint],
        now: datetime,
    ) -> float:

        if not tickets:
            return 100.0

        risk = 100.0

        for ticket in tickets:

            if not ticket.sla_deadline:
                continue

            seconds_remaining = (
                ticket.sla_deadline - now
            ).total_seconds()

            # Already breached.
            if seconds_remaining <= 0:
                risk -= 30
                continue

            hours_remaining = seconds_remaining / 3600

            if hours_remaining <= 1:
                risk -= 25

            elif hours_remaining <= 2:
                risk -= 15

            elif hours_remaining <= 4:
                risk -= 10

        return max(risk, 0.0)

    @classmethod
    def choose_agent(
        cls,
        db: Session,
        team: str,
        category: Optional[str],
        subcategory: Optional[str],
        priority_level: str,
    ) -> Optional[dict]:

        all_agents = (
            db.query(Agent)
            .filter(
                Agent.active.is_(True),
            )
            .all()
        )

        # --------------------------------------------------
        # RESOLVE LEGACY / HISTORICAL TEAM
        # --------------------------------------------------

        operational_team = (
            TeamService.resolve_for_assignment(
                team=team,
                category=category,
                subcategory=subcategory,
            )
        )

        # --------------------------------------------------
        # HARD OPERATIONAL TEAM FILTER
        # --------------------------------------------------

        agents = [
            agent
            for agent in all_agents
            if TeamService.matches(
                agent.team,
                operational_team,
            )
        ]

        if not agents:
            return None

        now = datetime.utcnow()

        def evaluate_candidates(
            candidate_agents,
            mode: str,
        ):

            candidates = []

            for agent in candidate_agents:

                # --------------------------------------------------
                # CURRENT WORKLOAD
                # --------------------------------------------------

                tickets = cls._get_active_tickets(
                    db,
                    agent.id,
                )

                workforce = (
                    WorkforceService.evaluate(
                        agent,
                        len(tickets),
                    )
                )

                workload = cls._calculate_workload(
                    tickets
                )

                capacity = (
                    workforce[
                        "max_concurrent_tickets"
                    ]
                )

                capacity_score, utilization = (
                    cls._capacity_score(
                        workload,
                        capacity,
                    )
                )

                # --------------------------------------------------
                # SKILL MATCH
                # --------------------------------------------------

                skill_score, skill_reasons = (
                    cls._skill_match(
                        agent,
                        category,
                        subcategory,
                    )
                )

                # --------------------------------------------------
                # HARD SKILL REQUIREMENT
                # --------------------------------------------------

                if mode == "NORMAL" and skill_score <= 0:
                    continue

                # --------------------------------------------------
                # HARD CAPACITY REQUIREMENT
                # --------------------------------------------------

                if mode == "NORMAL":

                    if not workforce["capacity_available"]:
                        continue

                    if utilization >= 1.0:
                        continue

                # --------------------------------------------------
                # PRIORITY / EXPERIENCE / SLA
                # --------------------------------------------------

                priority_load_score = (
                    cls._priority_load_score(
                        tickets
                    )
                )

                experience_score = (
                    cls._experience_score(
                        agent.experience_years
                    )
                )

                sla_risk_score = (
                    cls._sla_risk_score(
                        tickets,
                        now,
                    )
                )

                # --------------------------------------------------
                # NORMAL ROUTING
                # --------------------------------------------------

                if mode == "NORMAL":

                    score = (
                        capacity_score * 0.30
                        + skill_score * 0.30
                        + priority_load_score * 0.15
                        + experience_score * 0.10
                        + sla_risk_score * 0.15
                    )

                    reasons = [
                        "NORMAL SHIFT ROUTING",
                        (
                            f"Effective workload: "
                            f"{workload:.2f}"
                        ),
                        (
                            f"Capacity utilization: "
                            f"{utilization:.0%}"
                        ),
                        (
                            f"Skill fit: "
                            f"{skill_score:.0f}/100"
                        ),
                        (
                            "Priority workload health: "
                            f"{priority_load_score:.0f}/100"
                        ),
                        (
                            "Experience: "
                            f"{agent.experience_years or 0:g} years"
                        ),
                        (
                            "SLA exposure health: "
                            f"{sla_risk_score:.0f}/100"
                        ),
                    ]
                    if not TeamService.matches(
                        team,
                        operational_team,
                    ):
                        reasons.append(
                            f"Legacy team '{team}' resolved to "
                            f"operational team '{operational_team}'."
                        )

                # --------------------------------------------------
                # ON-CALL ROUTING
                # --------------------------------------------------

                else:

                    score = (
                        capacity_score * 0.25
                        + skill_score * 0.35
                        + priority_load_score * 0.15
                        + experience_score * 0.10
                        + sla_risk_score * 0.15
                    )

                    reasons = [
                        "ON-CALL ROUTING",
                        (
                            "Normal workforce unavailable; "
                            "emergency coverage selected."
                        ),
                        (
                            f"Effective workload: "
                            f"{workload:.2f}"
                        ),
                        (
                            f"Capacity utilization: "
                            f"{utilization:.0%}"
                        ),
                        (
                            f"Skill fit: "
                            f"{skill_score:.0f}/100"
                        ),
                        (
                            "Priority workload health: "
                            f"{priority_load_score:.0f}/100"
                        ),
                        (
                            "Experience: "
                            f"{agent.experience_years or 0:g} years"
                        ),
                        (
                            "SLA exposure health: "
                            f"{sla_risk_score:.0f}/100"
                        ),
                    ]

                # --------------------------------------------------
                # ADD SKILL REASONS
                # --------------------------------------------------

                reasons.extend(
                    skill_reasons
                )

                # --------------------------------------------------
                # ADD WORKFORCE INFORMATION
                # --------------------------------------------------

                reasons.extend(
                    [
                        (
                            "Availability: "
                            f"{agent.availability_status}"
                        ),
                        (
                            "Shift: "
                            f"{agent.shift_start}-"
                            f"{agent.shift_end}"
                        ),
                        (
                            "Timezone: "
                            f"{agent.timezone}"
                        ),
                        (
                            "Concurrent capacity: "
                            f"{len(tickets)}/"
                            f"{capacity}"
                        ),
                    ]
                )

                # --------------------------------------------------
                # CRITICAL TICKET PROTECTION
                # --------------------------------------------------

                critical_count = sum(
                    ticket.priority_level
                    == "Critical"
                    for ticket in tickets
                )

                if priority_level == "Critical":

                    if critical_count > 0:

                        score -= 25

                        reasons.append(
                            "Penalty: resolver already "
                            "owns Critical ticket(s)."
                        )

                    if utilization >= 1.0:

                        score -= 35

                        reasons.append(
                            "Penalty: resolver is at "
                            "or over capacity."
                        )

                # --------------------------------------------------
                # FINAL CANDIDATE
                # --------------------------------------------------

                candidates.append(
                    AssignmentCandidate(
                        agent=agent,
                        score=round(
                            max(score, 0),
                            2,
                        ),
                        workload=round(
                            workload,
                            2,
                        ),
                        utilization=round(
                            utilization,
                            3,
                        ),
                        skill_score=round(
                            skill_score,
                            2,
                        ),
                        capacity_score=round(
                            capacity_score,
                            2,
                        ),
                        priority_load_score=round(
                            priority_load_score,
                            2,
                        ),
                        experience_score=round(
                            experience_score,
                            2,
                        ),
                        sla_risk_score=round(
                            sla_risk_score,
                            2,
                        ),
                        reasons=reasons,
                    )
                )

            return candidates

        # ------------------------------------------------------
        # 1. NORMAL WORKFORCE
        # ------------------------------------------------------

        normal_agents = []

        for agent in agents:

            tickets = cls._get_active_tickets(
                db,
                agent.id,
            )

            workforce = (
                WorkforceService.evaluate(
                    agent,
                    len(tickets),
                )
            )

            if workforce["eligible"]:
                normal_agents.append(
                    agent
                )

        candidates = evaluate_candidates(
            normal_agents,
            "NORMAL",
        )

        # ------------------------------------------------------
        # 2. CRITICAL ON-CALL FALLBACK
        # ------------------------------------------------------

        if not candidates and priority_level == "Critical":

            on_call_agents = [
                agent
                for agent in agents
                if (
                    agent.on_call_enabled
                    and agent.active
                    and agent.auto_assignment_enabled
                )
            ]

            # For on-call, we deliberately do NOT require
            # normal shift eligibility.
            #
            # We still avoid OFFLINE / ON_LEAVE.
            on_call_agents = [
                agent
                for agent in on_call_agents
                if agent.availability_status
                in {
                    "AVAILABLE",
                    "BUSY",
                }
            ]

            candidates = evaluate_candidates(
                on_call_agents,
                "ON_CALL",
            )

        if not candidates:
            return None

        candidates.sort(
            key=lambda candidate: (
                candidate.score,
                -candidate.workload,
            ),
            reverse=True,
        )

        winner = candidates[0]

        mode = (
            "on-call"
            if any(
                "ON-CALL ROUTING" in reason
                for reason in winner.reasons
            )
            else "normal"
        )

        explanation = (
            f"Auto-assigned to "
            f"{winner.agent.name} "
            f"using {mode} routing. "

            f"Final score="
            f"{winner.score:.2f}. "

            f"Effective workload="
            f"{winner.workload:.2f}. "

            f"Capacity utilization="
            f"{winner.utilization:.0%}. "

            f"Capacity health="
            f"{winner.capacity_score:.0f}/100. "

            f"Skill fit="
            f"{winner.skill_score:.0f}/100. "

            f"Priority workload health="
            f"{winner.priority_load_score:.0f}/100. "

            f"SLA exposure health="
            f"{winner.sla_risk_score:.0f}/100. "

            f"Experience="
            f"{winner.agent.experience_years or 0:g} years."
        )

        return {
        "agent": winner.agent,
        "score": winner.score,
        "explanation": explanation,
        "load": winner.workload,
        "utilization": winner.utilization,
        "skill_score": winner.skill_score,
        "priority_load_score": (
            winner.priority_load_score
        ),
        "experience_score": (
            winner.experience_score
        ),
        "sla_risk_score": (
            winner.sla_risk_score
        ),
        "capacity_score": winner.capacity_score,
        "routing_mode": mode,
        "candidate_count": len(
            candidates
        ),
        "candidate_breakdown": [
            {
                "agent_id": (
                    candidate.agent.id
                ),
                "agent_name": (
                    candidate.agent.name
                ),
                "score": candidate.score,
                "workload": candidate.workload,
                "utilization": (
                    candidate.utilization
                ),
                "skill_score": (
                    candidate.skill_score
                ),
                "capacity_score": (
                    candidate.capacity_score
                ),
                "priority_load_score": (
                    candidate.priority_load_score
                ),
                "experience_score": (
                    candidate.experience_score
                ),
                "sla_risk_score": (
                    candidate.sla_risk_score
                ),
                "reasons": candidate.reasons,
            }
            for candidate in candidates
        ],
    }