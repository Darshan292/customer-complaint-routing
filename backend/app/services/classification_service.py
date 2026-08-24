class ClassificationService:

    CATEGORY_KEYWORDS = {
        "Fraud": [
            "unauthorized",
            "fraud",
            "stolen",
            "money transferred",
            "transaction",
            "payment"
        ],

        "Security": [
            "hacked",
            "breach",
            "compromised",
            "security"
        ],

        "Billing": [
            "invoice",
            "charge",
            "billing",
            "payment failed"
        ],

        "Refund": [
            "refund",
            "money back",
            "reimbursement"
        ],

        "Technical": [
            "bug",
            "error",
            "issue",
            "crash"
        ]
    }

    @classmethod
    def score_keywords(cls, text):

        text = text.lower()

        scores = {}

        for category, keywords in cls.CATEGORY_KEYWORDS.items():

            score = 0

            for keyword in keywords:

                if keyword in text:
                    score += 1

            scores[category] = score

        return scores

    @classmethod
    def get_final_category(
    cls,
    complaint_text,
    llm_category
    ):

      scores = cls.score_keywords(
        complaint_text
      )

      keyword_winner = max(
        scores,
        key=scores.get
      )

      keyword_score = scores[keyword_winner]

      if (keyword_score >= 2 and keyword_winner != llm_category):
        return keyword_winner

      return llm_category
