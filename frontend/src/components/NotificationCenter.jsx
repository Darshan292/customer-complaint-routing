import { useEffect, useRef, useState } from "react";
import API from "../services/api";
import { FiBell, FiCheck, FiCheckCircle, FiX } from "react-icons/fi";
import "./NotificationCenter.css";

function formatTime(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return date.toLocaleString([], {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function iconFor(type) {
  if (type === "TICKET_ASSIGNED") return "ASSIGNED";
  if (type === "TICKET_REASSIGNED") return "REASSIGNED";
  if (type === "STATUS_CHANGED") return "STATUS";
  if (type === "PRIORITY_CHANGED") return "PRIORITY";
  return "UPDATE";
}

export default function NotificationCenter() {
  const [notifications, setNotifications] = useState([]);
  const [unread, setUnread] = useState(0);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const firstLoad = useRef(true);

  const load = async () => {
    try {
      const [items, count] = await Promise.all([
        API.get("/notifications", {
          params: { limit: 30 },
        }),
        API.get("/notifications/unread-count"),
      ]);

      setNotifications(items.data || []);
      setUnread(count.data?.unread_count || 0);
    } catch (error) {
      // Notification failure should never break the dashboard.
      console.error("Notification center:", error);
    } finally {
      firstLoad.current = false;
    }
  };

  useEffect(() => {
    load();

    const timer = setInterval(load, 10000);
    return () => clearInterval(timer);
  }, []);

  const markRead = async (notification) => {
    if (notification.is_read) return;

    setLoading(true);

    try {
      await API.patch(
        `/notifications/${notification.id}/read`
      );

      await load();
    } finally {
      setLoading(false);
    }
  };

  const markAllRead = async () => {
    setLoading(true);

    try {
      await API.post(
        "/notifications/read-all"
      );

      await load();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="notification-center">
      <button
        type="button"
        className={`notification-trigger ${
          unread > 0 ? "has-unread" : ""
        }`}
        onClick={() => setOpen((value) => !value)}
        aria-label={`Notifications. ${unread} unread`}
      >
        <FiBell />

        {unread > 0 && (
          <span className="notification-count">
            {unread > 99 ? "99+" : unread}
          </span>
        )}
      </button>

      {open && (
        <div className="notification-popover">
          <div className="notification-head">
            <div>
              <span>NOTIFICATION CENTER</span>
              <strong>
                {unread
                  ? `${unread} unread`
                  : "All caught up"}
              </strong>
            </div>

            <div className="notification-head-actions">
              {unread > 0 && (
                <button
                  type="button"
                  onClick={markAllRead}
                  disabled={loading}
                  title="Mark all as read"
                >
                  <FiCheck /> Read all
                </button>
              )}

              <button
                type="button"
                className="notification-close"
                onClick={() => setOpen(false)}
              >
                <FiX />
              </button>
            </div>
          </div>

          <div className="notification-list">
            {notifications.length === 0 ? (
              <div className="notification-empty">
                <FiCheckCircle />
                <strong>No notifications</strong>
                <span>
                  Assignment, status and priority updates will appear here.
                </span>
              </div>
            ) : (
              notifications.map((notification) => (
                <button
                  type="button"
                  key={notification.id}
                  className={`notification-item ${
                    notification.is_read
                      ? "read"
                      : "unread"
                  }`}
                  onClick={() =>
                    markRead(notification)
                  }
                >
                  <div className="notification-item-mark">
                    <span>
                      {iconFor(
                        notification.notification_type
                      )}
                    </span>
                  </div>

                  <div className="notification-item-body">
                    <div className="notification-item-title">
                      <strong>
                        {notification.title}
                      </strong>

                      {!notification.is_read && (
                        <i />
                      )}
                    </div>

                    <p>
                      {notification.message}
                    </p>

                    <time>
                      {formatTime(
                        notification.created_at
                      )}
                    </time>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
