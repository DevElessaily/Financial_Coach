
from typing import ClassVar, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    DEFAULT_DASHBOARD_WIDGETS: ClassVar[list[str]] = [
        "stats_overview",
        "recent_transactions",
        "top_transactions",
        "top_categories",
    ]

    Id: Mapped[int] = mapped_column("id", primary_key=True, index=True)

    Name: Mapped[str] = mapped_column("name", String(150), nullable=False)
    Email: Mapped[str] = mapped_column(
        "email", String(255), unique=True, index=True, nullable=False
    )
    Password: Mapped[str] = mapped_column("password", String(255), nullable=False)

    BudgetId: Mapped[Optional[int]] = mapped_column(
        "budget_id", ForeignKey("budgets.id"), nullable=True
    )

    Language: Mapped[Optional[str]] = mapped_column(
        "language", String(10), nullable=True
    )

    AlertViaEmail: Mapped[bool] = mapped_column(
        "alert_via_email", Boolean, default=False, nullable=False
    )

    DashboardWidgets: Mapped[Optional[list]] = mapped_column(
        "dashboard_widgets",
        JSON,
        default=lambda: User.DEFAULT_DASHBOARD_WIDGETS.copy(),
        nullable=True,
    )

    # Multi-factor authentication
    MfaSecret: Mapped[Optional[str]] = mapped_column(
        "mfa_secret", String(255), nullable=True
    )

    MfaRecoveryCodes: Mapped[Optional[list]] = mapped_column(
        "mfa_recovery_codes", JSON, nullable=True
    )

    MfaRequired: Mapped[bool] = mapped_column(
        "mfa_required", Boolean, default=False, nullable=False
    )

    EmailVerifiedAt: Mapped[Optional[DateTime]] = mapped_column(
        "email_verified_at", DateTime(timezone=True), nullable=True
    )

    RememberToken: Mapped[Optional[str]] = mapped_column(
        "remember_token", String(100), nullable=True
    )

    CreatedAt: Mapped[Optional[DateTime]] = mapped_column(
        "created_at", DateTime(timezone=True), nullable=True
    )

    UpdatedAt: Mapped[Optional[DateTime]] = mapped_column(
        "updated_at", DateTime(timezone=True), nullable=True
    )

    # Relationships
    DeviceTokens: Mapped[list["DeviceToken"]] = relationship(
        "DeviceToken",
        back_populates="User",
        cascade="all, delete-orphan",
    )

    def GetAppAuthenticationSecret(self) -> Optional[str]:
        return self.MfaSecret

    def SaveAppAuthenticationSecret(self, Secret: Optional[str]) -> None:
        self.MfaSecret = Secret

    def GetAppAuthenticationHolderName(self) -> str:
        return self.Email

    def GetAppAuthenticationRecoveryCodes(self) -> Optional[list]:
        return self.MfaRecoveryCodes

    def SaveAppAuthenticationRecoveryCodes(
        self, Codes: Optional[list]
    ) -> None:
        self.MfaRecoveryCodes = Codes

    def RouteNotificationForApn(self) -> list[str]:
        return [
            DeviceToken.DeviceToken
            for DeviceToken in self.DeviceTokens
            if DeviceToken.Platform == "ios"
        ]
