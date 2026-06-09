import hmac
import logging
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.core.mail import send_mail
from django.db import transaction
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework.exceptions import APIException, AuthenticationFailed
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from apps.accounts.models import UserAccountStatus

logger = logging.getLogger(__name__)
EMAIL_VERIFICATION_SALT = "accounts.email-verification"


class GoogleLoginNotConfigured(APIException):
    status_code = 503
    default_detail = (
        "Google login is not configured yet. Add GOOGLE_OAUTH_CLIENT_ID before "
        "enabling this sign-in method."
    )
    default_code = "google_login_not_configured"


class InvalidGoogleIdentity(AuthenticationFailed):
    default_detail = "Google identity could not be verified."
    default_code = "invalid_google_identity"


def blacklist_user_refresh_tokens(user):
    for outstanding_token in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=outstanding_token)


def build_password_reset_url(user):
    query = urlencode(
        {
            "uid": urlsafe_base64_encode(force_bytes(user.pk)),
            "token": default_token_generator.make_token(user),
        }
    )
    return f"{settings.FRONTEND_BASE_URL.rstrip('/')}/reset-password?{query}"


def send_password_reset_email(user):
    reset_url = build_password_reset_url(user)
    # TODO(email-provider): Configure SES/Resend/Postmark through a Django email
    # backend and store provider credentials in environment/AWS secrets.
    return send_mail(
        subject="Reset your password",
        message=(
            "Use the following link to reset your password. "
            f"The link expires according to the server password-reset policy:\n\n{reset_url}"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


def build_email_verification_token(user):
    return signing.dumps(
        {"user_id": user.pk, "email": user.email},
        salt=EMAIL_VERIFICATION_SALT,
        compress=True,
    )


def build_email_verification_url(user):
    query = urlencode({"token": build_email_verification_token(user)})
    return f"{settings.FRONTEND_BASE_URL.rstrip('/')}/verify-email?{query}"


def send_email_verification_email(user):
    verification_url = build_email_verification_url(user)
    # TODO(email-provider): Configure SES/Resend/Postmark through a Django email
    # backend and store provider credentials in environment/AWS secrets.
    return send_mail(
        subject="Verify your email address",
        message=(
            "Use the following link to verify your email address. "
            f"The link expires after {settings.EMAIL_VERIFICATION_MAX_AGE} seconds:"
            f"\n\n{verification_url}"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )


@transaction.atomic
def verify_email_verification_token(token):
    try:
        payload = signing.loads(
            token,
            salt=EMAIL_VERIFICATION_SALT,
            max_age=settings.EMAIL_VERIFICATION_MAX_AGE,
        )
    except (signing.BadSignature, signing.SignatureExpired) as exc:
        raise ValueError("This email verification link is invalid or expired.") from exc

    user = (
        get_user_model()
        .objects.select_for_update()
        .filter(pk=payload.get("user_id"), email__iexact=payload.get("email", ""))
        .first()
    )
    if (
        user is None
        or not user.is_active
        or user.account_status != UserAccountStatus.ACTIVE
    ):
        raise ValueError("This email verification link is invalid or expired.")
    if not user.is_email_verified:
        user.is_email_verified = True
        user.save(update_fields=["is_email_verified"])
    return user


def google_login_configuration(nonce=""):
    client_id = settings.GOOGLE_OAUTH_CLIENT_ID
    return {"enabled": bool(client_id), "client_id": client_id, "nonce": nonce if client_id else ""}


def verify_google_identity_token(credential, expected_nonce):
    client_id = settings.GOOGLE_OAUTH_CLIENT_ID
    if not client_id:
        raise GoogleLoginNotConfigured()
    if not expected_nonce:
        raise InvalidGoogleIdentity("Google login session is missing or expired.")

    try:
        from google.auth.transport.requests import Request
        from google.oauth2 import id_token
    except ImportError as exc:
        raise GoogleLoginNotConfigured(
            "Google login dependencies are not installed in this environment."
        ) from exc

    try:
        claims = id_token.verify_oauth2_token(credential, Request(), client_id)
    except Exception as exc:
        logger.info("Google identity verification failed.", exc_info=exc)
        raise InvalidGoogleIdentity() from exc

    if claims.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}:
        raise InvalidGoogleIdentity()
    if claims.get("email_verified") not in {True, "true"} or not claims.get("email"):
        raise InvalidGoogleIdentity("Google account email is not verified.")
    claim_nonce = claims.get("nonce", "")
    if not claim_nonce or not hmac.compare_digest(str(claim_nonce), expected_nonce):
        raise InvalidGoogleIdentity("Google login session is missing or expired.")
    return claims


@transaction.atomic
def get_or_create_google_user(claims):
    User = get_user_model()
    email = User.objects.normalize_email(claims["email"])
    user = User.objects.select_for_update().filter(email__iexact=email).first()
    if user is None:
        user = User.objects.create_user(
            email=email,
            password=None,
            name=(claims.get("name") or "")[:255],
            is_email_verified=True,
        )
    elif not user.is_active or user.account_status != UserAccountStatus.ACTIVE:
        raise AuthenticationFailed("This account is not active.")
    else:
        update_fields = []
        if not user.is_email_verified:
            user.is_email_verified = True
            update_fields.append("is_email_verified")
        if not user.name and claims.get("name"):
            user.name = claims["name"][:255]
            update_fields.append("name")
        if update_fields:
            user.save(update_fields=update_fields)

    if not user.organization_memberships.filter(status="active").exists():
        from apps.organizations.services import create_organization_for_owner

        create_organization_for_owner(user, f"{user.email}'s workspace")
    return user


def get_password_reset_user(uid):
    try:
        user_id = force_str(urlsafe_base64_decode(uid))
        return get_user_model().objects.filter(pk=user_id).first()
    except (TypeError, ValueError, OverflowError):
        return None


@transaction.atomic
def reset_user_password(*, user, new_password):
    user.set_password(new_password)
    user.save(update_fields=["password"])
    blacklist_user_refresh_tokens(user)
    return user
