import { Check, CheckCheck, Mail, Save } from "lucide-react";
import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";

import { PageHeader } from "../components/PageHeader";
import { EmptyState, ErrorState, LoadingState, SuccessState } from "../components/StateBlock";
import { StatusBadge } from "../components/StatusBadge";
import { api, getApiErrorMessage, listResults } from "../lib/api";
import { useAuth } from "../lib/auth";
import { formatDate } from "../lib/format";
import { isOrganizationAdmin, useWorkspace } from "../lib/workspace";

export function NotificationsPage() {
  const queryClient = useQueryClient();
  const { accessToken, user } = useAuth();
  const { selectedOrganization } = useWorkspace();
  const organizationId = selectedOrganization?.id;
  const canViewDeliveryLogs = isOrganizationAdmin(selectedOrganization);
  const [event, setEvent] = useState("report_ready");
  const [channel, setChannel] = useState("email");
  const [isEnabled, setIsEnabled] = useState(true);

  const preferencesQuery = useQuery({
    enabled: Boolean(accessToken && organizationId),
    queryKey: ["notification-preferences", organizationId],
    queryFn: () => api.notificationPreferences(accessToken, organizationId!),
  });
  const deliveryLogsQuery = useQuery({
    enabled: Boolean(accessToken && organizationId && canViewDeliveryLogs),
    queryKey: ["notification-delivery-logs", organizationId],
    queryFn: () => api.notificationDeliveryLogs(accessToken, organizationId!),
  });
  const inAppNotificationsQuery = useQuery({
    enabled: Boolean(accessToken && organizationId),
    queryKey: ["in-app-notifications", organizationId],
    queryFn: () => api.inAppNotifications(accessToken, organizationId!),
  });

  const preferences = listResults(preferencesQuery.data);
  const deliveryLogs = listResults(deliveryLogsQuery.data);
  const inAppNotifications = listResults(inAppNotificationsQuery.data);

  const savePreferenceMutation = useMutation({
    mutationFn: () =>
      api.upsertNotificationPreference(accessToken, {
        organization_id: organizationId!,
        user_id: user?.id,
        event,
        channel,
        is_enabled: isEnabled,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notification-preferences", organizationId] });
    },
  });
  const markReadMutation = useMutation({
    mutationFn: (notificationId: number) =>
      api.markInAppNotificationRead(accessToken, notificationId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["in-app-notifications", organizationId] });
    },
  });
  const markAllReadMutation = useMutation({
    mutationFn: () => api.markAllInAppNotificationsRead(accessToken, organizationId!),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["in-app-notifications", organizationId] });
    },
  });

  function handleSavePreference(eventSubmit: FormEvent<HTMLFormElement>) {
    eventSubmit.preventDefault();
    savePreferenceMutation.mutate();
  }

  return (
    <>
      <PageHeader eyebrow="Notifications" icon={Mail} title="Preferences and Delivery">
        <form className="inline-form" onSubmit={handleSavePreference}>
          <select
            aria-label="Notification event"
            onChange={(inputEvent) => setEvent(inputEvent.target.value)}
            value={event}
          >
            <option value="report_ready">Report ready</option>
            <option value="report_failed">Report failed</option>
            <option value="billing_event">Billing event</option>
            <option value="system_alert">System alert</option>
          </select>
          <select
            aria-label="Notification channel"
            onChange={(inputEvent) => setChannel(inputEvent.target.value)}
            value={channel}
          >
            <option value="email">Email</option>
            <option value="in_app">In-app</option>
            <option value="webhook">Webhook</option>
          </select>
          <label className="toggle-control">
            <input
              checked={isEnabled}
              onChange={(inputEvent) => setIsEnabled(inputEvent.target.checked)}
              type="checkbox"
            />
            Enabled
          </label>
          <button
            className="primary-button"
            disabled={!organizationId || savePreferenceMutation.isPending}
            type="submit"
          >
            <Save aria-hidden="true" size={18} />
            {savePreferenceMutation.isPending ? "Saving" : "Save"}
          </button>
        </form>
      </PageHeader>

      {preferencesQuery.isLoading ||
      inAppNotificationsQuery.isLoading ||
      (canViewDeliveryLogs && deliveryLogsQuery.isLoading) ? (
        <LoadingState title="Loading notifications" />
      ) : null}
      {preferencesQuery.isError ||
      inAppNotificationsQuery.isError ||
      (canViewDeliveryLogs && deliveryLogsQuery.isError) ? (
        <ErrorState title="Notifications unavailable" />
      ) : null}
      {savePreferenceMutation.isError ? (
        <ErrorState
          detail={getApiErrorMessage(savePreferenceMutation.error)}
          title="Preference save failed"
        />
      ) : null}
      {savePreferenceMutation.isSuccess ? (
        <SuccessState title="Notification preference saved" />
      ) : null}

      <section className="tool-panel">
        <div className="panel-heading">
          <h2>Notification Center</h2>
          <button
            className="secondary-button panel-action"
            disabled={
              !inAppNotifications.some((notification) => !notification.is_read) ||
              markAllReadMutation.isPending
            }
            onClick={() => markAllReadMutation.mutate()}
            type="button"
          >
            <CheckCheck aria-hidden="true" size={17} />
            Mark all read
          </button>
        </div>
        {inAppNotifications.length ? (
          <div className="compact-list">
            {inAppNotifications.map((notification) => (
              <div className="compact-row" key={notification.id}>
                <div>
                  <strong>{notification.title}</strong>
                  <span>{notification.message || formatDate(notification.created_at)}</span>
                  {notification.target_url ? <Link to={notification.target_url}>Open</Link> : null}
                </div>
                {notification.is_read ? (
                  <StatusBadge value="read" />
                ) : (
                  <button
                    aria-label={`Mark ${notification.title} read`}
                    className="secondary-button panel-action"
                    disabled={markReadMutation.isPending}
                    onClick={() => markReadMutation.mutate(notification.id)}
                    type="button"
                  >
                    <Check aria-hidden="true" size={17} />
                    Read
                  </button>
                )}
              </div>
            ))}
          </div>
        ) : (
          <EmptyState title="No in-app notifications" />
        )}
      </section>

      <section className="split-grid">
        <div className="tool-panel">
          <div className="panel-heading">
            <h2>Preferences</h2>
          </div>
          {preferences.length ? (
            <div className="compact-list">
              {preferences.map((preference) => (
                <div className="compact-row" key={preference.id}>
                  <div>
                    <strong>{preference.event.replaceAll("_", " ")}</strong>
                    <span>{preference.channel}</span>
                  </div>
                  <StatusBadge value={preference.is_enabled ? "active" : "disabled"} />
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="No preferences" />
          )}
        </div>

        <div className="tool-panel">
          <div className="panel-heading">
            <h2>Delivery Logs</h2>
          </div>
          {deliveryLogs.length ? (
            <div className="compact-list">
              {deliveryLogs.slice(0, 10).map((log) => (
                <div className="compact-row" key={log.id}>
                  <div>
                    <strong>{log.subject || log.event.replaceAll("_", " ")}</strong>
                    <span>{formatDate(log.created_at)}</span>
                  </div>
                  <StatusBadge value={log.status} />
                </div>
              ))}
            </div>
          ) : (
            <EmptyState title="No delivery logs" />
          )}
        </div>
      </section>
    </>
  );
}
