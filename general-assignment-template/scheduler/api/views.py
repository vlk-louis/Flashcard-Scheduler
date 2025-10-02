from rest_framework import views, status
from rest_framework.response import Response
import structlog
import uuid
from ..services.reviews import record_review
from ..utils.time import to_jst_iso
from ..data.models import CardSchedule
from .serializers import ReviewInSerializer, DueQuerySerializer

base_logger = structlog.get_logger()


class ReviewView(views.APIView):
    def post(self, request):
        # Create a unique request_id
        request_id = str(uuid.uuid4())
        logger = base_logger.bind(request_id=request_id)

        s = ReviewInSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        user_id = s.validated_data["user_id"]
        card_id = s.validated_data["card_id"]
        rating = s.validated_data["rating"]
        idem = s.validated_data["idempotency_key"]

        next_dt, interval_s, was_idem = record_review(user_id, card_id, rating, idem)
        status_code = status.HTTP_200_OK if was_idem else status.HTTP_201_CREATED

        # Log with request_id & relevant context
        logger.info(
            "review_api_response",
            user_id=str(user_id),
            card_id=str(card_id),
            rating=rating,
            idempotent=was_idem,
            interval_seconds=interval_s,
            next_review_utc=next_dt.isoformat(),
            next_review_jst=to_jst_iso(next_dt),
            status=status_code,
        )

        return Response(
            {
                "next_review_utc": next_dt.isoformat(),
                "next_review_jst": to_jst_iso(next_dt),
                "interval_seconds": interval_s,
                "rating_label": {0: "分からない", 1: "分かる", 2: "簡単"}[rating],
                "idempotent": was_idem,
            },
            status=status_code,
        )


class DueCardsView(views.APIView):
    def get(self, request, user_id):
        # Create a unique request_id
        request_id = str(uuid.uuid4())
        logger = base_logger.bind(request_id=request_id)

        qs = DueQuerySerializer(data=request.query_params)
        qs.is_valid(raise_exception=True)
        until = qs.validated_data["until"]

        card_ids = (
            CardSchedule.objects.filter(user_id=user_id, next_review_at__lte=until)
            .values_list("card_id", flat=True)
        )
        results = list(card_ids)

        logger.info(
            "due_cards_api_response",
            user_id=str(user_id),
            until_utc=until.isoformat(),
            until_jst=to_jst_iso(until),
            card_count=len(results),
        )

        return Response(
            {
                "user_id": str(user_id),
                "until_utc": until.isoformat(),
                "until_jst": to_jst_iso(until),
                "card_ids": results,
            }
        )