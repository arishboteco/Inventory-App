/**
 * Unified Notification System
 *
 * Consolidates all toast/message/notification functionality into a single system.
 * Replaces multiple duplicate implementations across the codebase.
 *
 * Features:
 * - Multiple display types (toast, banner, inline)
 * - Auto-dismiss with configurable timing
 * - Accessibility support (ARIA labels, screen reader friendly)
 * - Animation support
 * - Queue management for multiple notifications
 */

class NotificationManager {
  constructor() {
    this.container = null;
    this.notifications = [];
    this.maxNotifications = 5;
    this.defaultDuration = 5000;
    this.init();
  }

  init() {
    const ensure = () => {
      this.container = document.getElementById("notification-container");
      if (!this.container) {
        this.container = document.createElement("div");
        this.container.id = "notification-container";
        this.container.className =
          "fixed top-4 right-4 space-y-2 z-50 max-w-sm";
        this.container.setAttribute("aria-live", "polite");
        this.container.setAttribute("aria-label", "Notifications");
        document.body.appendChild(this.container);
      }
    };
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", ensure, { once: true });
    } else {
      ensure();
    }
  }

  /**
   * Show a toast notification (floating, auto-dismiss)
   * @param {string} message - The message to display
   * @param {string} type - Type: 'success', 'error', 'warning', 'info'
   * @param {number} duration - Duration in ms (0 = no auto-dismiss)
   * @param {object} options - Additional options
   */
  showToast(message, type = "info", duration = null, options = {}) {
    return this.show(message, type, duration, { ...options, style: "toast" });
  }

  /**
   * Show a banner notification (full width, persistent until dismissed)
   * @param {string} message - The message to display
   * @param {string} type - Type: 'success', 'error', 'warning', 'info'
   * @param {object} options - Additional options
   */
  showBanner(message, type = "info", options = {}) {
    return this.show(message, type, 0, { ...options, style: "banner" });
  }

  /**
   * Show an inline notification (for form validation, etc.)
   * @param {HTMLElement} target - Element to attach notification to
   * @param {string} message - The message to display
   * @param {string} type - Type: 'success', 'error', 'warning', 'info'
   * @param {number} duration - Duration in ms (0 = no auto-dismiss)
   */
  showInline(target, message, type = "info", duration = null) {
    // Remove existing inline notifications on this target
    const existing = target.parentNode.querySelector(".notification-inline");
    if (existing) existing.remove();

    const notification = this.createNotificationElement(
      message,
      type,
      "inline",
    );
    notification.className += " notification-inline mt-2";

    target.parentNode.insertBefore(notification, target.nextSibling);

    const notificationData = {
      id: this.generateId(),
      element: notification,
      timer: null,
    };

    if (duration !== 0) {
      const dismissTime = duration || this.defaultDuration;
      notificationData.timer = setTimeout(() => {
        this.dismiss(notificationData.id);
      }, dismissTime);
    }

    this.notifications.push(notificationData);
    return notificationData.id;
  }

  /**
   * Core show method
   */
  show(message, type = "info", duration = null, options = {}) {
    const style = options.style || "toast";

    if (style === "banner") {
      return this.showBannerNotification(message, type, options);
    }

    // Manage queue for toast notifications
    if (this.notifications.length >= this.maxNotifications) {
      this.dismiss(this.notifications[0].id);
    }

    const notification = this.createNotificationElement(
      message,
      type,
      style,
      options,
    );
    this.container.appendChild(notification);

    const notificationData = {
      id: this.generateId(),
      element: notification,
      timer: null,
    };

    // Animate in
    requestAnimationFrame(() => {
      notification.style.transform = "translateX(0)";
      notification.style.opacity = "1";
    });

    // Auto-dismiss
    if (duration !== 0) {
      const dismissTime = duration || this.defaultDuration;
      notificationData.timer = setTimeout(() => {
        this.dismiss(notificationData.id);
      }, dismissTime);
    }

    this.notifications.push(notificationData);
    return notificationData.id;
  }

  createNotificationElement(message, type, style, options = {}) {
    const notification = document.createElement("div");
    const baseClasses =
      "px-4 py-3 rounded-lg shadow-lg flex items-start gap-3 transition-all duration-300";

    // Type-specific styles
    const typeStyles = {
      success: "bg-success text-white",
      error: "bg-red-500 text-white",
      warning: "bg-warning text-white",
      info: "bg-blue-500 text-white",
    };

    // Style-specific classes
    const styleClasses = {
      toast: "transform translate-x-full opacity-0",
      banner: "w-full",
      inline: "text-sm",
    };

    notification.className = `${baseClasses} ${typeStyles[type]} ${styleClasses[style]}`;

    // Accessibility
    notification.setAttribute("role", "alert");
    notification.setAttribute("aria-live", "assertive");

    // Icon
    const icon = this.getIcon(type);
    if (icon) {
      const iconElement = document.createElement("span");
      iconElement.innerHTML = icon;
      iconElement.className = "flex-shrink-0";
      notification.appendChild(iconElement);
    }

    // Message
    const messageElement = document.createElement("span");
    messageElement.className = "flex-1";
    messageElement.textContent = message;
    notification.appendChild(messageElement);

    // Dismiss button
    if (options.dismissible !== false) {
      const dismissButton = document.createElement("button");
      dismissButton.innerHTML = "&times;";
      dismissButton.className =
        "flex-shrink-0 text-xl leading-none opacity-70 hover:opacity-100";
      dismissButton.setAttribute("aria-label", "Dismiss notification");
      dismissButton.onclick = () =>
        this.dismiss(notification.dataset.notificationId);
      notification.appendChild(dismissButton);
    }

    return notification;
  }

  showBannerNotification(message, type, options) {
    // Remove existing banner
    const existingBanner = document.querySelector(".notification-banner");
    if (existingBanner) existingBanner.remove();

    const banner = this.createNotificationElement(
      message,
      type,
      "banner",
      options,
    );
    banner.className += " notification-banner fixed top-0 left-0 right-0 z-50";

    document.body.insertBefore(banner, document.body.firstChild);

    // Adjust body padding to accommodate banner
    document.body.style.paddingTop = banner.offsetHeight + "px";

    const notificationData = {
      id: this.generateId(),
      element: banner,
      timer: null,
    };

    this.notifications.push(notificationData);
    return notificationData.id;
  }

  /**
   * Dismiss a notification by ID
   */
  dismiss(notificationId) {
    const notificationIndex = this.notifications.findIndex(
      (n) => n.id === notificationId,
    );
    if (notificationIndex === -1) return;

    const notification = this.notifications[notificationIndex];

    // Clear timer
    if (notification.timer) {
      clearTimeout(notification.timer);
    }

    // Animate out
    if (notification.element.classList.contains("notification-banner")) {
      // Special handling for banner
      notification.element.style.transform = "translateY(-100%)";
      document.body.style.paddingTop = "0";
    } else {
      notification.element.style.transform = "translateX(100%)";
      notification.element.style.opacity = "0";
    }

    // Remove from DOM
    setTimeout(() => {
      if (notification.element.parentNode) {
        notification.element.parentNode.removeChild(notification.element);
      }
    }, 300);

    // Remove from tracking
    this.notifications.splice(notificationIndex, 1);
  }

  /**
   * Clear all notifications
   */
  clearAll() {
    this.notifications.forEach((notification) => {
      this.dismiss(notification.id);
    });
  }

  getIcon(type) {
    const icons = {
      success: "✅",
      error: "❌",
      warning: "⚠️",
      info: "ℹ️",
    };
    return icons[type];
  }

  generateId() {
    return (
      "notification-" +
      Date.now() +
      "-" +
      Math.random().toString(36).substr(2, 9)
    );
  }
}

// Create global instance
window.notifications = new NotificationManager();

// Backward compatibility functions
window.showToast = (message, type, duration) =>
  window.notifications.showToast(message, type, duration);
window.showMessage = (message, type, duration) =>
  window.notifications.showToast(message, type, duration);
window.showNotification = (message, type, duration) =>
  window.notifications.showToast(message, type, duration);

// Export for module usage
if (typeof module !== "undefined" && module.exports) {
  module.exports = NotificationManager;
}

// Bridge: detect server-sent markers and convert to toasts (e.g., <!-- toast: msg -->)
function triggerToastsFromComments(root) {
  try {
    const walker = document.createTreeWalker(
      root || document.body,
      NodeFilter.SHOW_COMMENT,
      null,
    );
    let node;
    while ((node = walker.nextNode())) {
      const val = (node.nodeValue || "").trim();
      const m = val.match(/^toast:\s*([\s\S]*)$/i);
      if (m) {
        const msg = (m[1] || "").trim();
        if (msg) window.notifications.showToast(msg, "success");
      }
    }
  } catch (_) {
    // no-op
  }
}

document.addEventListener("DOMContentLoaded", () => {
  triggerToastsFromComments(document.body);
});

document.addEventListener("htmx:afterSwap", (e) => {
  // Prefer DOM walk over regex on response text for robustness
  const target = (e && e.detail && e.detail.target) || null;
  if (target instanceof Element) {
    triggerToastsFromComments(target);
    return;
  }
  // Fallback: parse responseText when target not available
  try {
    const frag = e.detail && e.detail.xhr ? e.detail.xhr.responseText || "" : "";
    if (!frag) return;
    const re = /<!--\s*toast:\s*([^]+?)\s*-->/gi;
    let m;
    while ((m = re.exec(frag)) !== null) {
      const msg = (m[1] || "").trim();
      if (msg) window.notifications.showToast(msg, "success");
    }
  } catch (_) {
    // no-op
  }
});
