import json

from app.schemas.analysis_schema import AnalysisResult


class ParserService:

    @staticmethod
    def parse(raw_response: str):

        data = json.loads(raw_response)

        if data["confidence"] > 1:
            data["confidence"] = (
                data["confidence"] / 100
            )

        return AnalysisResult(**data)