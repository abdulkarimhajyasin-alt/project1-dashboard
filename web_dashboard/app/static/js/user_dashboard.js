(function () {
  const body = document.body;
  const userDrawer = document.querySelector("[data-user-drawer]");
  const userOverlay = document.querySelector("[data-user-drawer-overlay]");
  const userOpenButtons = document.querySelectorAll("[data-user-drawer-open]");
  const userCloseButtons = document.querySelectorAll("[data-user-drawer-close]");
  const userNavLinks = document.querySelectorAll("[data-user-drawer-nav] a");
  const notificationRoots = document.querySelectorAll("[data-notification-root]");
  const supportChatModal = document.querySelector("[data-support-chat-modal]");
  const supportChatOpenButtons = document.querySelectorAll("[data-support-chat-open]");
  const supportChatCloseButtons = document.querySelectorAll("[data-support-chat-close]");
  const supportFileInputs = document.querySelectorAll("[data-support-file-input]");
  const userMessageModal = document.querySelector("[data-user-message-modal]");
  const unverifiedWarningModal = document.querySelector("[data-unverified-warning-modal]");
  const unverifiedWarningCloseButtons = document.querySelectorAll("[data-unverified-warning-close]");
  const unverifiedWarningVerifyButton = document.querySelector("[data-unverified-warning-verify]");
  const verificationModal = document.querySelector("[data-user-verification-modal]");
  const verificationOpenButton = document.querySelector("[data-user-verification-open]");
  const verificationCloseButtons = document.querySelectorAll("[data-user-verification-close]");
  const verificationForm = document.querySelector("[data-verification-form]");
  const verificationConfirmModal = document.querySelector("[data-verification-confirm-modal]");
  const verificationConfirmSubmit = document.querySelector("[data-verification-confirm-submit]");
  const verificationConfirmBack = document.querySelector("[data-verification-confirm-back]");
  const verificationFlash = document.querySelector("[data-verification-flash]");
  const documentTypeSelect = document.querySelector("[data-document-type]");
  const dualDocumentFields = document.querySelector("[data-dual-document-fields]");
  const passportDocumentField = document.querySelector("[data-passport-document-field]");
  const profitWithdrawModal = document.querySelector("[data-profit-withdraw-modal]");
  const profitWithdrawOpenButton = document.querySelector("[data-profit-withdraw-open]");
  const profitWithdrawCloseButtons = document.querySelectorAll("[data-profit-withdraw-close]");
  const profitWithdrawForm = document.querySelector("[data-profit-withdraw-form]");
  const profitWithdrawFields = document.querySelector("[data-profit-withdraw-fields]");
  const profitWithdrawConfirm = document.querySelector("[data-profit-withdraw-confirm]");
  const profitWithdrawConfirmText = document.querySelector("[data-profit-withdraw-confirm-text]");
  const profitWithdrawConfirmSubmit = document.querySelector("[data-profit-withdraw-confirm-submit]");
  const profitWithdrawConfirmCancel = document.querySelector("[data-profit-withdraw-confirm-cancel]");
  const profitWithdrawMessage = document.querySelector("[data-profit-withdraw-message]");
  const profitWithdrawPrimaryActions = document.querySelector("[data-profit-withdraw-primary-actions]");
  const imageExtensions = [".gif", ".jpeg", ".jpg", ".png", ".webp"];
  const maxVerificationImageSize = 5 * 1024 * 1024;
  const unverifiedWarningStorageKey = "novahash_unverified_warning_last_seen";
  const unverifiedWarningIntervalMs = 60 * 60 * 1000;
  const verificationImageLabels = {
    front: "صورة الوجه الأمامي",
    back: "صورة الوجه الخلفي",
    passport: "صورة جواز السفر",
  };
  let unverifiedWarningTimer = null;
  let pendingProfitWithdrawFormData = null;

  function formatFileSize(size) {
    if (!Number.isFinite(size)) return "";
    if (size < 1024 * 1024) {
      return `${Math.max(1, Math.round(size / 1024))} KB`;
    }
    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  }

  function isImageFile(file) {
    const fileName = (file.name || "").toLowerCase();
    return file.type.startsWith("image/") || imageExtensions.some(function (extension) {
      return fileName.endsWith(extension);
    });
  }

  function setupSupportFilePreview() {
    supportFileInputs.forEach(function (input) {
      const form = input.closest("form");
      const preview = form?.querySelector("[data-support-file-preview]");
      const image = form?.querySelector("[data-support-file-preview-image]");
      const icon = form?.querySelector("[data-support-file-preview-icon]");
      const name = form?.querySelector("[data-support-file-preview-name]");
      const meta = form?.querySelector("[data-support-file-preview-meta]");
      const clearButton = form?.querySelector("[data-support-file-clear]");
      let objectUrl = "";

      if (!preview || !image || !icon || !name || !meta || !clearButton) return;

      function resetPreview() {
        if (objectUrl) {
          URL.revokeObjectURL(objectUrl);
          objectUrl = "";
        }
        input.value = "";
        image.src = "";
        image.hidden = true;
        icon.hidden = false;
        name.textContent = "";
        meta.textContent = "";
        preview.hidden = true;
      }

      input.addEventListener("change", function () {
        if (objectUrl) {
          URL.revokeObjectURL(objectUrl);
          objectUrl = "";
        }

        const file = input.files?.[0];
        if (!file) {
          resetPreview();
          return;
        }

        name.textContent = file.name;
        meta.textContent = `${file.type || "ملف"} - ${formatFileSize(file.size)}`;

        if (isImageFile(file)) {
          objectUrl = URL.createObjectURL(file);
          image.src = objectUrl;
          image.hidden = false;
          icon.hidden = true;
        } else {
          image.src = "";
          image.hidden = true;
          icon.hidden = false;
        }

        preview.hidden = false;
      });

      clearButton.addEventListener("click", resetPreview);
      form?.addEventListener("submit", function () {
        if (objectUrl) URL.revokeObjectURL(objectUrl);
      });
    });
  }

  function setSupportChatOpen(isOpen) {
    if (!supportChatModal) return;
    supportChatModal.classList.toggle("is-open", isOpen);
    supportChatModal.setAttribute("aria-hidden", String(!isOpen));
    body.classList.toggle("support-chat-open", isOpen);
  }

  function closeUserMessageModal() {
    if (!userMessageModal) return;
    userMessageModal.classList.remove("is-open");
    userMessageModal.setAttribute("aria-hidden", "true");
  }

  function getStoredUnverifiedWarningTime() {
    try {
      return Number(window.localStorage.getItem(unverifiedWarningStorageKey) || 0);
    } catch (error) {
      return 0;
    }
  }

  function rememberUnverifiedWarningTime() {
    const now = Date.now();
    try {
      window.localStorage.setItem(unverifiedWarningStorageKey, String(now));
    } catch (error) {
      // localStorage can be unavailable in private or restricted browsers.
    }
    return now;
  }

  function clearUnverifiedWarningTimer() {
    if (!unverifiedWarningTimer) return;
    window.clearTimeout(unverifiedWarningTimer);
    unverifiedWarningTimer = null;
  }

  function scheduleUnverifiedWarning(delayMs) {
    if (!unverifiedWarningModal || body.dataset.userVerified === "true") return;
    clearUnverifiedWarningTimer();
    unverifiedWarningTimer = window.setTimeout(function () {
      setUnverifiedWarningOpen(true, false);
    }, Math.max(0, delayMs));
  }

  function setUnverifiedWarningOpen(isOpen, shouldRemember) {
    if (!unverifiedWarningModal) return;
    const wasOpen = unverifiedWarningModal.classList.contains("is-open");
    unverifiedWarningModal.classList.toggle("is-open", isOpen);
    unverifiedWarningModal.setAttribute("aria-hidden", String(!isOpen));
    if (isOpen) {
      clearUnverifiedWarningTimer();
    }
    if (!isOpen && shouldRemember && wasOpen) {
      rememberUnverifiedWarningTime();
      scheduleUnverifiedWarning(unverifiedWarningIntervalMs);
    }
  }

  function maybeShowUnverifiedWarning() {
    if (!unverifiedWarningModal || body.dataset.userVerified === "true") return;
    const lastSeenAt = getStoredUnverifiedWarningTime();
    const elapsedMs = lastSeenAt ? Date.now() - lastSeenAt : unverifiedWarningIntervalMs;
    if (elapsedMs >= unverifiedWarningIntervalMs) {
      scheduleUnverifiedWarning(700);
      return;
    }
    scheduleUnverifiedWarning(unverifiedWarningIntervalMs - elapsedMs);
  }

  function setProfitWithdrawModalOpen(isOpen) {
    if (!profitWithdrawModal) return;
    profitWithdrawModal.classList.toggle("is-open", isOpen);
    profitWithdrawModal.setAttribute("aria-hidden", String(!isOpen));
    body.classList.toggle("profit-withdraw-modal-open", isOpen);
    if (!isOpen) {
      resetProfitWithdrawForm();
    }
  }

  function setProfitWithdrawMessage(message, isError) {
    if (!profitWithdrawMessage) return;
    profitWithdrawMessage.textContent = message || "";
    profitWithdrawMessage.hidden = !message;
    profitWithdrawMessage.classList.toggle("is-error", Boolean(isError));
  }

  function setProfitWithdrawLoading(isLoading) {
    if (!profitWithdrawConfirmSubmit) return;
    profitWithdrawConfirmSubmit.disabled = isLoading;
    profitWithdrawConfirmSubmit.textContent = isLoading ? "جاري الإرسال..." : "تأكيد";
  }

  function resetProfitWithdrawForm() {
    pendingProfitWithdrawFormData = null;
    profitWithdrawForm?.reset();
    if (profitWithdrawFields) profitWithdrawFields.hidden = false;
    if (profitWithdrawConfirm) profitWithdrawConfirm.hidden = true;
    if (profitWithdrawPrimaryActions) profitWithdrawPrimaryActions.hidden = false;
    setProfitWithdrawLoading(false);
    setProfitWithdrawMessage("", false);
  }

  function formatArabicCountdown(totalSeconds) {
    const safeSeconds = Math.max(0, Math.floor(Number(totalSeconds || 0)));
    const days = Math.floor(safeSeconds / 86400);
    const hours = Math.floor((safeSeconds % 86400) / 3600);
    const minutes = Math.floor((safeSeconds % 3600) / 60);
    const seconds = safeSeconds % 60;
    return `${days.toString().padStart(2, "0")} يوم ${hours.toString().padStart(2, "0")} ساعة ${minutes.toString().padStart(2, "0")} دقيقة ${seconds.toString().padStart(2, "0")} ثانية`;
  }

  function setVerificationModalOpen(modal, isOpen) {
    if (!modal) return;
    modal.classList.toggle("is-open", isOpen);
    modal.setAttribute("aria-hidden", String(!isOpen));
    body.classList.toggle("verification-modal-open", Boolean(document.querySelector(".user-verification-modal.is-open")));
    if (modal === verificationModal && !isOpen) {
      dismissVerificationFlash();
    }
  }

  function clearVerificationSentParam() {
    const url = new URL(window.location.href);
    if (!url.searchParams.has("verification_sent")) return;
    url.searchParams.delete("verification_sent");
    window.history.replaceState(window.history.state, "", `${url.pathname}${url.search}${url.hash}`);
  }

  function dismissVerificationFlash() {
    if (!verificationFlash || !verificationFlash.isConnected) {
      clearVerificationSentParam();
      return;
    }
    verificationFlash.remove();
    clearVerificationSentParam();
  }

  function clearVerificationFileInput(input) {
    if (!input) return;
    input.value = "";
    const key = input.dataset.verificationPreview;
    const preview = document.querySelector(`[data-verification-preview-image="${key}"]`);
    if (!preview) return;
    if (preview.dataset.objectUrl) {
      URL.revokeObjectURL(preview.dataset.objectUrl);
      delete preview.dataset.objectUrl;
    }
    preview.src = "";
    preview.hidden = true;
  }

  function setVerificationGroupActive(group, isActive) {
    if (!group) return;
    group.hidden = !isActive;
    group.classList.toggle("is-hidden", !isActive);
    group.setAttribute("aria-hidden", String(!isActive));
    group.querySelectorAll("input[type='file']").forEach(function (input) {
      input.disabled = !isActive;
      input.required = isActive;
      input.setCustomValidity("");
      if (!isActive) {
        clearVerificationFileInput(input);
      }
    });
  }

  function updateVerificationDocumentFields() {
    if (!documentTypeSelect || !dualDocumentFields || !passportDocumentField) return;
    const isPassport = documentTypeSelect.value === "passport";
    setVerificationGroupActive(dualDocumentFields, !isPassport);
    setVerificationGroupActive(passportDocumentField, isPassport);
  }

  function setupVerificationPreviews() {
    document.querySelectorAll("[data-verification-preview]").forEach(function (input) {
      input.addEventListener("change", function () {
        const key = input.dataset.verificationPreview;
        const preview = document.querySelector(`[data-verification-preview-image="${key}"]`);
        const file = input.files?.[0];
        if (!preview) return;
        if (!file) {
          clearVerificationFileInput(input);
          return;
        }
        if (preview.dataset.objectUrl) {
          URL.revokeObjectURL(preview.dataset.objectUrl);
        }
        const objectUrl = URL.createObjectURL(file);
        preview.dataset.objectUrl = objectUrl;
        preview.src = objectUrl;
        preview.hidden = false;
      });
    });
  }

  function validateVerificationFiles() {
    if (!documentTypeSelect) return true;
    const activeGroup = documentTypeSelect.value === "passport" ? passportDocumentField : dualDocumentFields;
    const inputs = Array.from(activeGroup?.querySelectorAll("input[type='file']") || []);
    for (const input of inputs) {
      input.setCustomValidity("");
      const file = input.files?.[0];
      const label = verificationImageLabels[input.dataset.verificationPreview] || "الصورة المطلوبة";
      if (!file) {
        input.setCustomValidity(`يرجى رفع ${label}.`);
        input.reportValidity();
        return false;
      }
      if (!isImageFile(file)) {
        input.setCustomValidity(`${label} يجب أن تكون صورة.`);
        input.reportValidity();
        return false;
      }
      if (file.size > maxVerificationImageSize) {
        input.setCustomValidity(`${label} يجب ألا تتجاوز 5MB.`);
        input.reportValidity();
        return false;
      }
    }
    return true;
  }

  supportChatOpenButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      setSupportChatOpen(true);
      loadSupportMessages();
    });
  });

  supportChatCloseButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      setSupportChatOpen(false);
    });
  });

  if (supportChatModal) {
    supportChatModal.addEventListener("click", function (event) {
      if (event.target === supportChatModal) {
        setSupportChatOpen(false);
      }
    });
  }

  function closeNotifications(exceptRoot) {
    notificationRoots.forEach(function (root) {
      if (root === exceptRoot) return;
      root.classList.remove("is-open");
      const toggle = root.querySelector("[data-notification-toggle]");
      const panel = root.querySelector("[data-notification-panel]");
      if (toggle) toggle.setAttribute("aria-expanded", "false");
      if (panel) panel.setAttribute("aria-hidden", "true");
    });
  }

  notificationRoots.forEach(function (root) {
    const toggle = root.querySelector("[data-notification-toggle]");
    const panel = root.querySelector("[data-notification-panel]");
    if (!toggle) return;

    toggle.addEventListener("click", function (event) {
      event.stopPropagation();
      const isOpen = !root.classList.contains("is-open");
      closeNotifications(root);
      root.classList.toggle("is-open", isOpen);
      toggle.setAttribute("aria-expanded", String(isOpen));
      if (panel) panel.setAttribute("aria-hidden", String(!isOpen));
    });
  });

  const realtimeToast = (function () {
    const toast = document.createElement("div");
    toast.className = "realtime-toast";
    toast.hidden = true;
    document.body.appendChild(toast);
    let timer = null;
    return function (message) {
      toast.textContent = message;
      toast.hidden = false;
      window.clearTimeout(timer);
      timer = window.setTimeout(function () {
        toast.hidden = true;
      }, 3200);
    };
  })();

  function escapeHtml(value) {
    return String(value || "").replace(/[&<>"']/g, function (char) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;" }[char];
    });
  }

  function latestNotificationIdFromDom() {
    const first = document.querySelector(".notification-item[href*='/open']");
    const match = first?.getAttribute("href")?.match(/\/(\d+)\/open/);
    return match ? Number(match[1]) : 0;
  }

  let latestRealtimeNotificationId = latestNotificationIdFromDom();
  let notificationPollTimer = null;
  let notificationPollInFlight = false;

  function renderNotifications(payload) {
    notificationRoots.forEach(function (root) {
      const count = Number(payload.unread_count || 0);
      const bell = root.querySelector("[data-notification-toggle]");
      root.querySelector(".notification-badge")?.remove();
      if (count > 0 && bell) {
        const badge = document.createElement("span");
        badge.className = "notification-badge";
        badge.textContent = String(count);
        bell.appendChild(badge);
      }
      const tools = root.querySelector(".notification-panel-tools span");
      if (tools) tools.textContent = `${count} جديد`;
      const clearButton = root.querySelector("[data-notification-clear-button]");
      if (clearButton) {
        clearButton.hidden = count <= 0;
        clearButton.disabled = count <= 0;
      }
      const list = root.querySelector(".notification-list");
      if (!list) return;
      const notifications = Array.isArray(payload.notifications) ? payload.notifications : [];
      if (!notifications.length) {
        list.innerHTML = '<article class="notification-empty"><strong>لا توجد إشعارات حالياً</strong><p>سيظهر هنا لاحقاً كل تنبيه جديد.</p></article>';
        return;
      }
      list.innerHTML = notifications.map(function (item) {
        return `
          <a class="notification-item ${escapeHtml(item.kind || "system")}" href="${escapeHtml(item.open_url || "/user/notifications")}">
            <strong>${escapeHtml(item.title)}</strong>
            <p>${escapeHtml(item.message)}</p>
            <small>${escapeHtml(item.created_label || "")}</small>
          </a>
        `;
      }).join("");
    });
  }

  function normalizeSupportMessage(message) {
    if (!message || typeof message !== "object") return null;
    const senderType = message.sender_type || message.sender || message.role || "user";
    const body = message.body ?? message.content ?? "";
    return {
      ...message,
      sender_type: senderType,
      sender_label: message.sender_label || (senderType === "admin" ? "الدعم" : "أنت"),
      body: String(body || ""),
      has_attachment: Boolean(message.has_attachment || message.attachment_url),
      is_image: Boolean(message.is_image),
      attachment_url: message.attachment_url || "",
      created_label: message.created_label || "",
    };
  }

  function normalizeSupportMessages(messages) {
    if (!Array.isArray(messages)) {
      console.error("[support-chat] Expected messages array.", messages);
      return null;
    }
    return messages.map(normalizeSupportMessage).filter(Boolean);
  }

  function renderSupportMessages(messages) {
    const bodyEl = supportChatModal?.querySelector("[data-support-chat-body]");
    if (!bodyEl) {
      console.error("[support-chat] Message container not found.");
      return;
    }
    const normalizedMessages = normalizeSupportMessages(messages);
    if (!normalizedMessages) return;
    const previousLast = Number(bodyEl.querySelector("[data-support-message-id]:last-child")?.dataset.supportMessageId || 0);
    bodyEl.innerHTML = normalizedMessages.map(supportMessageHtml).join("") || '<div class="support-chat-empty"><strong>لا توجد رسائل بعد</strong><p>ابدأ المحادثة برسالة واضحة.</p></div>';
    const nextLast = Number(normalizedMessages[normalizedMessages.length - 1]?.id || 0);
    if (nextLast > previousLast) bodyEl.scrollTop = bodyEl.scrollHeight;
    updateSupportComposeState(normalizedMessages);
  }

  function supportMessageHtml(message) {
    const normalizedMessage = normalizeSupportMessage(message);
    if (!normalizedMessage) return "";
    return `
      <article class="support-bubble ${normalizedMessage.sender_type === "admin" ? "from-admin" : "from-user"}" data-support-message-id="${normalizedMessage.id}">
        <div class="support-bubble-meta">
          <strong>${escapeHtml(normalizedMessage.sender_label || "")}</strong>
          <small>${escapeHtml(normalizedMessage.created_label || "")}</small>
        </div>
        ${normalizedMessage.body ? `<p>${escapeHtml(normalizedMessage.body)}</p>` : ""}
        ${normalizedMessage.has_attachment ? (normalizedMessage.is_image ? `<img src="${escapeHtml(normalizedMessage.attachment_url)}" class="chat-image" alt="attachment">` : `<a href="${escapeHtml(normalizedMessage.attachment_url)}">تحميل الملف</a>`) : ""}
      </article>
    `;
  }

  function appendSupportMessage(message) {
    const bodyEl = supportChatModal?.querySelector("[data-support-chat-body]");
    if (!bodyEl) {
      console.error("[support-chat] Message container not found.");
      return;
    }
    const normalizedMessage = normalizeSupportMessage(message);
    if (!normalizedMessage || bodyEl.querySelector(`[data-support-message-id="${normalizedMessage.id}"]`)) return;
    bodyEl.querySelector(".support-chat-empty")?.remove();
    bodyEl.insertAdjacentHTML("beforeend", supportMessageHtml(normalizedMessage));
    bodyEl.scrollTop = bodyEl.scrollHeight;
    updateSupportComposeState([normalizedMessage]);
  }

  function updateSupportComposeState(messages) {
    const compose = supportChatModal?.querySelector("[data-support-compose]");
    const waitingForAdmin = messages[messages.length - 1]?.sender_type === "user";
    if (compose) compose.dataset.waitingForAdmin = String(waitingForAdmin);
    compose?.querySelectorAll("textarea, input, button[type='submit']").forEach(function (field) {
      field.disabled = waitingForAdmin;
    });
  }

  function loadSupportMessages() {
    if (!supportChatModal?.classList.contains("is-open")) return Promise.resolve();
    const messagesUrl = supportChatModal.dataset.supportMessagesUrl || "/user/support/messages";
    console.debug("[support-chat] Loading messages from", messagesUrl);
    return fetch(messagesUrl, {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    })
      .then(function (response) {
        if (!response.ok) {
          throw new Error(`GET ${messagesUrl} failed with ${response.status}`);
        }
        return response.json();
      })
      .then(function (payload) {
        if (!payload || payload.ok !== true) {
          console.error("[support-chat] Unexpected messages response.", payload);
          return;
        }
        if (!Array.isArray(payload.messages)) {
          console.error("[support-chat] Response messages is not an array.", payload);
          return;
        }
        if (payload.thread_id) supportChatModal.dataset.supportThreadId = String(payload.thread_id);
        renderSupportMessages(payload.messages);
      })
      .catch(function (error) {
        console.error("[support-chat] Failed to load messages.", error);
      });
  }

  function pollNotifications(forceToast) {
    if (notificationPollInFlight) return Promise.resolve();
    notificationPollInFlight = true;
    const threadId = supportChatModal?.classList.contains("is-open") ? supportChatModal.dataset.supportThreadId : "";
    const query = threadId ? `?thread_id=${encodeURIComponent(threadId)}` : "";
    return fetch(`/user/notifications/poll${query}`, {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    })
      .then(function (response) {
        return response.ok ? response.json() : null;
      })
      .then(function (payload) {
        if (!payload) return;
        renderNotifications(payload);
        const latest = Number(payload.latest_notification_id || 0);
        if (latest > latestRealtimeNotificationId && (latestRealtimeNotificationId || forceToast)) {
          realtimeToast(payload.notifications?.[0]?.title || "New notification");
        }
        latestRealtimeNotificationId = Math.max(latestRealtimeNotificationId, latest);
      })
      .finally(function () {
        notificationPollInFlight = false;
      });
  }

  function scheduleNotificationPoll() {
    window.clearTimeout(notificationPollTimer);
    const delay = document.hidden ? 15000 : 3000;
    notificationPollTimer = window.setTimeout(function () {
      pollNotifications().finally(scheduleNotificationPoll);
    }, delay);
  }

  if (!window.__novaUserNotificationPollingStarted) {
    window.__novaUserNotificationPollingStarted = true;
    scheduleNotificationPoll();
    document.addEventListener("visibilitychange", function () {
      if (!document.hidden) pollNotifications(true);
      scheduleNotificationPoll();
    });
    window.addEventListener("beforeunload", function () {
      window.clearTimeout(notificationPollTimer);
    });
  }

  document.addEventListener("click", function (event) {
    const notificationLink = event.target.closest(".notification-item[href*='/open']");
    if (!notificationLink) return;
    const badge = notificationLink.closest("[data-notification-root]")?.querySelector(".notification-badge");
    if (badge) {
      const next = Math.max(0, Number(badge.textContent || 0) - 1);
      badge.textContent = String(next);
      if (!next) badge.remove();
    }
  });

  notificationRoots.forEach(function (root) {
    const clearForm = root.querySelector("[data-notification-clear-form]");
    clearForm?.addEventListener("submit", function (event) {
      event.preventDefault();
      const button = clearForm.querySelector("[data-notification-clear-button]");
      if (button) button.disabled = true;
      fetch(clearForm.action, {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Accept": "application/json",
          "X-Requested-With": "fetch",
        },
      })
        .then(function (response) {
          return response.ok ? response.json() : Promise.reject(new Error("تعذر مسح الإشعارات."));
        })
        .then(function (payload) {
          renderNotifications(payload);
          latestRealtimeNotificationId = Number(payload.latest_notification_id || 0);
        })
        .catch(function (error) {
          realtimeToast(error.message || "تعذر مسح الإشعارات.");
          if (button) button.disabled = false;
        });
    });
  });

  supportChatModal?.querySelector("[data-support-compose]")?.addEventListener("submit", function (event) {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector("button[type='submit']");
    if (button) button.disabled = true;
    fetch(form.action, {
      method: "POST",
      body: new FormData(form),
      credentials: "same-origin",
      headers: { "X-Requested-With": "fetch", Accept: "application/json" },
    })
      .then(function (response) {
        return response.json().then(function (data) {
          return { ok: response.ok, data };
        });
      })
      .then(function (result) {
        if (!result.ok || result.data.ok === false) throw new Error(result.data.error || "Could not send message.");
        form.reset();
        form.querySelector("[data-support-file-clear]")?.click();
        if (Array.isArray(result.data.messages) && result.data.messages.length) {
          renderSupportMessages(result.data.messages);
        } else if (result.data.message) {
          appendSupportMessage(result.data.message);
        }
        loadSupportMessages();
        pollNotifications(true);
      })
      .catch(function (error) {
        realtimeToast(error.message || "Could not send message.");
      })
      .finally(function () {
        if (button && form.dataset.waitingForAdmin !== "true") button.disabled = false;
      });
  });

  function setUserDrawerOpen(isOpen) {
    if (!userDrawer) return;
    body.classList.toggle("user-menu-open", isOpen);
    userDrawer.classList.toggle("is-open", isOpen);
    userOverlay?.classList.toggle("is-visible", isOpen);
    userDrawer.setAttribute("aria-hidden", String(!isOpen));
    userOverlay?.setAttribute("aria-hidden", String(!isOpen));
    userOpenButtons.forEach(function (button) {
      button.setAttribute("aria-expanded", String(isOpen));
    });
  }

  userOpenButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      setUserDrawerOpen(true);
    });
  });

  userCloseButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      setUserDrawerOpen(false);
    });
  });

  userOverlay?.addEventListener("click", function () {
    setUserDrawerOpen(false);
  });

  userNavLinks.forEach(function (link) {
    link.addEventListener("click", function () {
      setUserDrawerOpen(false);
    });
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      setUserDrawerOpen(false);
      closeNotifications();
      setSupportChatOpen(false);
      closeUserMessageModal();
      setUnverifiedWarningOpen(false, true);
      setVerificationModalOpen(verificationModal, false);
      setVerificationModalOpen(verificationConfirmModal, false);
    }
  });

  document.addEventListener("click", function (event) {
    if (!event.target.closest("[data-notification-root]")) {
      closeNotifications();
    }
  });

  setUserDrawerOpen(false);
  closeNotifications();
  setupSupportFilePreview();
  setSupportChatOpen(supportChatModal ? supportChatModal.classList.contains("is-open") : false);
  loadSupportMessages();

  const ring = document.querySelector(".mining-ring");
  const progressCircle = document.querySelector(".ring-progress");
  const percentText = document.getElementById("ringPercent");
  const countdownText = document.getElementById("miningCountdown");
  const startForm = document.querySelector("[data-mining-start-form]");
  const remainingText = document.querySelector("[data-remaining-time]");
  const miningStatusLabel = document.querySelector("[data-mining-status-label]");
  const cycleIdText = document.querySelector("[data-cycle-id]");
  const startTimeText = document.querySelector("[data-start-time]");
  const actualStartTimeText = document.querySelector("[data-actual-start-time]");
  const endTimeText = document.querySelector("[data-end-time]");
  const missedTimeText = document.querySelector("[data-missed-time]");
  const earningRatioText = document.querySelector("[data-earning-ratio]");
  const expectedEarnedIncomeText = document.querySelector("[data-expected-earned-income]");
  const liveBalanceText = document.querySelector("[data-live-balance]");
  const liveBalanceMode = document.querySelector("[data-live-balance-mode]");
  const miningCoreNote = document.querySelector("[data-mining-core-note]");
  const startError = document.querySelector("[data-mining-start-error]");
  const startButton = document.querySelector("[data-start-mining-button]");
  const radius = 150;
  const circumference = 2 * Math.PI * radius;
  let liveBalanceAnimationFrame = null;
  let liveBalanceState = {
    activeSeconds: 0,
    actualStartAt: 0,
    currentTotalBalance: 0,
    expectedEarnedIncome: 0,
    isActive: false,
  };

  function clamp(value, min, max) {
    return Math.min(Math.max(value, min), max);
  }

  function setRingProgress(value) {
    if (!progressCircle || !percentText) return;
    const progress = clamp(value, 0, 100);
    const offset = circumference - (progress / 100) * circumference;
    progressCircle.style.strokeDasharray = `${circumference}`;
    progressCircle.style.strokeDashoffset = `${offset}`;
    percentText.textContent = `${Math.round(progress)}%`;
  }

  function formatRemaining(seconds) {
    const safeSeconds = Math.max(0, Math.floor(seconds));
    const hours = String(Math.floor(safeSeconds / 3600)).padStart(2, "0");
    const minutes = String(Math.floor((safeSeconds % 3600) / 60)).padStart(2, "0");
    const secs = String(safeSeconds % 60).padStart(2, "0");
    return `${hours}:${minutes}:${secs}`;
  }

  function formatRatioPercent(value) {
    const ratio = Number(value || 0);
    return `${(ratio * 100).toFixed(2)}%`;
  }

  function formatMoney(value, decimals) {
    return `$${Number(value || 0).toFixed(decimals)}`;
  }

  function parseMoneyNumber(value) {
    const parsed = Number.parseFloat(value);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function formatLiveBalance(value) {
    return `$${Math.max(0, value).toFixed(8)}`;
  }

  function stopLiveBalanceAnimation() {
    if (!liveBalanceAnimationFrame) return;
    window.cancelAnimationFrame(liveBalanceAnimationFrame);
    liveBalanceAnimationFrame = null;
  }

  function getVisualBalance(now) {
    if (!liveBalanceState.isActive || !liveBalanceState.actualStartAt || liveBalanceState.activeSeconds <= 0) {
      return liveBalanceState.currentTotalBalance;
    }

    const elapsedActiveSeconds = clamp((now - liveBalanceState.actualStartAt) / 1000, 0, liveBalanceState.activeSeconds);
    const visualEarnings = liveBalanceState.expectedEarnedIncome * (elapsedActiveSeconds / liveBalanceState.activeSeconds);
    return liveBalanceState.currentTotalBalance + visualEarnings;
  }

  function renderLiveBalance() {
    if (!liveBalanceText) return;
    const visualBalance = getVisualBalance(Date.now());
    liveBalanceText.textContent = formatLiveBalance(visualBalance);
    liveBalanceText.classList.toggle("is-live", liveBalanceState.isActive);
    liveBalanceText.closest(".live-balance-card")?.classList.toggle("is-live", liveBalanceState.isActive);
    if (liveBalanceMode) {
      liveBalanceMode.textContent = liveBalanceState.isActive ? "Live Available Yield" : "Available Yield";
    }
  }

  function animateLiveBalance() {
    renderLiveBalance();
    if (liveBalanceState.isActive) {
      liveBalanceAnimationFrame = window.requestAnimationFrame(animateLiveBalance);
    }
  }

  function updateLiveBalanceFromStatus(status) {
    if (!liveBalanceText || !status) return;
    const currentTotalBalance = parseMoneyNumber(status.current_total_balance ?? liveBalanceText.dataset.currentTotalBalance);
    const expectedEarnedIncome = parseMoneyNumber(status.expected_earned_income ?? liveBalanceText.dataset.expectedEarnedIncome);
    const activeSeconds = Number(status.active_seconds || liveBalanceText.dataset.activeSeconds || 0);
    const actualStartAt = status.actual_start_time_iso
      ? Date.parse(status.actual_start_time_iso)
      : Date.parse(liveBalanceText.dataset.actualStartAt || "");
    const isActive =
      !status.completed &&
      status.can_start === false &&
      status.status === "active" &&
      expectedEarnedIncome > 0 &&
      activeSeconds > 0 &&
      Number.isFinite(actualStartAt);

    liveBalanceState = {
      activeSeconds,
      actualStartAt: Number.isFinite(actualStartAt) ? actualStartAt : 0,
      currentTotalBalance,
      expectedEarnedIncome,
      isActive,
    };

    liveBalanceText.dataset.currentTotalBalance = String(currentTotalBalance);
    liveBalanceText.dataset.expectedEarnedIncome = String(expectedEarnedIncome);
    liveBalanceText.dataset.activeSeconds = String(activeSeconds);
    liveBalanceText.dataset.actualStartAt = status.actual_start_time_iso || "";
    liveBalanceText.dataset.endAt = status.end_time_iso || "";
    liveBalanceText.dataset.cycleStatus = status.status || "ready";
    liveBalanceText.dataset.canStart = status.can_start ? "true" : "false";

    stopLiveBalanceAnimation();
    if (isActive) {
      animateLiveBalance();
    } else {
      renderLiveBalance();
    }
  }

  function titleCase(value) {
    return String(value || "ready").replace(/\b\w/g, function (letter) {
      return letter.toUpperCase();
    });
  }

  function showMiningError(message) {
    if (!startError) return;
    startError.textContent = message || "Could not start mining cycle. Please try again.";
    startError.hidden = false;
  }

  function clearMiningError() {
    if (!startError) return;
    startError.textContent = "";
    startError.hidden = true;
  }

  if (liveBalanceText) {
    updateLiveBalanceFromStatus({
      active_seconds: Number(liveBalanceText.dataset.activeSeconds || 0),
      actual_start_time_iso: liveBalanceText.dataset.actualStartAt || "",
      can_start: liveBalanceText.dataset.canStart === "true",
      completed: false,
      current_total_balance: liveBalanceText.dataset.currentTotalBalance || "0",
      end_time_iso: liveBalanceText.dataset.endAt || "",
      expected_earned_income: liveBalanceText.dataset.expectedEarnedIncome || "0",
      status: liveBalanceText.dataset.cycleStatus || "ready",
    });
  }

  if (ring) {
    let currentProgress = Number(ring.dataset.progress || 0);
    let currentCanStart = ring.dataset.canStart === "true";
    let currentDuration = Number(ring.dataset.duration || 86400);
    let currentStartAt = ring.dataset.startAt ? Date.parse(ring.dataset.startAt) : 0;
    let currentEndAt = ring.dataset.endAt ? Date.parse(ring.dataset.endAt) : 0;
    let completionChecked = false;
    let animatedProgress = 0;
    let introTimer = window.setInterval(function () {
      animatedProgress += Math.max(1, currentProgress / 24);
      if (animatedProgress >= currentProgress) {
        animatedProgress = currentProgress;
        window.clearInterval(introTimer);
        introTimer = null;
      }
      setRingProgress(animatedProgress);
    }, 18);

    function updateStartButton(isLoading) {
      if (!startButton) return;
      startButton.classList.toggle("is-loading", Boolean(isLoading));
      if (isLoading) {
        startButton.disabled = true;
        startButton.textContent = "Starting...";
        return;
      }
      startButton.disabled = !currentCanStart;
      startButton.textContent = currentCanStart ? "Start" : "Mining Active";
    }

    function applyMiningStatus(status) {
      if (!status) return;
      if (introTimer) {
        window.clearInterval(introTimer);
        introTimer = null;
      }

      currentCanStart = Boolean(status.can_start);
      currentProgress = Number(status.completed ? 100 : status.progress_percent || 0);
      currentDuration = Number(status.duration_seconds || status.duration || ring.dataset.duration || 86400);
      currentStartAt = status.start_time_iso ? Date.parse(status.start_time_iso) : 0;
      currentEndAt = status.end_time_iso ? Date.parse(status.end_time_iso) : 0;
      completionChecked = Boolean(status.completed);

      ring.dataset.progress = String(currentProgress);
      ring.dataset.canStart = currentCanStart ? "true" : "false";
      ring.dataset.duration = String(currentDuration);
      ring.dataset.startAt = status.start_time_iso || "";
      ring.dataset.endAt = status.end_time_iso || "";
      ring.dataset.status = status.status || "ready";

      setRingProgress(currentProgress);
      if (miningStatusLabel) miningStatusLabel.textContent = status.completed ? "Completed" : titleCase(status.status);
      if (cycleIdText) cycleIdText.textContent = status.cycle_id || "-";
      if (startTimeText) startTimeText.textContent = status.start_time || "-";
      if (actualStartTimeText) actualStartTimeText.textContent = status.actual_start_time || "-";
      if (endTimeText) endTimeText.textContent = status.end_time || "-";

      const remainingLabel = formatRemaining(Number(status.remaining_seconds || 0));
      const missedLabel = formatRemaining(Number(status.missed_seconds || 0));
      if (remainingText) remainingText.textContent = currentCanStart ? "00:00:00" : remainingLabel;
      if (missedTimeText) missedTimeText.textContent = currentCanStart ? "00:00:00" : missedLabel;
      if (earningRatioText) earningRatioText.textContent = formatRatioPercent(status.earning_ratio);
      if (expectedEarnedIncomeText) expectedEarnedIncomeText.textContent = formatMoney(status.expected_earned_income, 4);
      updateLiveBalanceFromStatus(status);
      if (countdownText) {
        if (status.completed) {
          countdownText.textContent = `Completed. Added $${status.completed_income || "0.0000"}`;
        } else {
          countdownText.textContent = currentCanStart ? "Ready to start" : `Remaining ${remainingLabel}`;
        }
      }
      if (miningCoreNote) {
        miningCoreNote.textContent = currentCanStart
          ? "Press Start to join the current official 18:00 daily cycle. Late starts earn only the remaining active time."
          : "Your current mining cycle is active until the next 18:00 in your timezone.";
      }
      updateStartButton(false);
    }

    function refreshMiningStatus() {
      return fetch("/user/mining/status", {
        credentials: "same-origin",
        headers: { Accept: "application/json" },
      })
        .then(function (response) {
          return response.ok ? response.json() : null;
        })
        .then(function (data) {
          if (!data) return null;
          applyMiningStatus(data);
          return data;
        });
    }

    function tickMiningCycle() {
      if (currentCanStart) return;
      const now = Date.now();
      const elapsed = currentStartAt && currentEndAt ? (now - currentStartAt) / 1000 : (currentProgress / 100) * currentDuration;
      const remaining = currentEndAt ? (currentEndAt - now) / 1000 : currentDuration - elapsed;
      const liveProgress = clamp((elapsed / currentDuration) * 100, currentProgress, 100);
      setRingProgress(liveProgress);

      const remainingLabel = formatRemaining(remaining);
      if (remainingText) remainingText.textContent = remainingLabel;
      if (countdownText) countdownText.textContent = liveProgress >= 100 ? "Completing cycle..." : `Remaining ${remainingLabel}`;

      if (liveProgress >= 100 && !completionChecked) {
        completionChecked = true;
        refreshMiningStatus().catch(function () {
          if (countdownText) countdownText.textContent = "Cycle complete. Refresh to claim status.";
        });
      }
    }

    updateStartButton(false);
    if (currentCanStart) {
      if (countdownText) countdownText.textContent = "Ready to start";
      if (remainingText) remainingText.textContent = "00:00:00";
    }
    tickMiningCycle();
    window.setInterval(tickMiningCycle, 1000);

    if (startForm) {
      startForm.addEventListener("submit", function (event) {
        event.preventDefault();
        if (!currentCanStart || !startButton) return;

        clearMiningError();
        updateStartButton(true);

        fetch(startForm.action, {
          credentials: "same-origin",
          headers: {
            Accept: "application/json",
            "X-Requested-With": "fetch",
          },
          method: "POST",
        })
          .then(function (response) {
            return response.json().catch(function () {
              return null;
            }).then(function (data) {
              if (!response.ok || (data && data.ok === false)) {
                if (data && data.status) applyMiningStatus(data.status);
                throw new Error((data && data.error) || "Could not start mining cycle. Please try again.");
              }
              return data;
            });
          })
          .then(function (data) {
            if (!data) {
              throw new Error("Could not read mining status. Please refresh and try again.");
            }
            applyMiningStatus(data && data.status ? data.status : data);
          })
          .catch(function (error) {
            showMiningError(error.message);
            updateStartButton(false);
          });
      });
    }
  }

  document.querySelectorAll("[data-counter]").forEach(function (counter) {
    const rawValue = Number(counter.dataset.counter || 0);
    const isMoney = counter.textContent.trim().startsWith("$");
    const decimals = counter.textContent.includes(".") ? counter.textContent.trim().split(".")[1].replace(/[^0-9]/g, "").length : 0;
    let frame = 0;
    const totalFrames = 42;
    const timer = window.setInterval(function () {
      frame += 1;
      const eased = 1 - Math.pow(1 - frame / totalFrames, 3);
      const value = rawValue * eased;
      counter.textContent = `${isMoney ? "$" : ""}${value.toFixed(decimals)}`;
      if (frame >= totalFrames) {
        counter.textContent = `${isMoney ? "$" : ""}${rawValue.toFixed(decimals)}`;
        window.clearInterval(timer);
      }
    }, 18);
  });

  document.querySelectorAll(".withdraw-progress").forEach(function (bar) {
    const value = clamp(Number(bar.dataset.withdraw || 0), 0, 100);
    const fill = bar.querySelector("span");
    const label = bar.querySelector("strong");
    window.setTimeout(function () {
      if (fill) fill.style.width = `${value}%`;
      if (label) label.textContent = `${Math.round(value)}%`;
    }, 250);
  });

  document.querySelectorAll("[data-withdraw-countdown]").forEach(function (counter) {
    let remaining = Math.max(0, Number(counter.dataset.remainingSeconds || 0));
    function renderCountdown() {
      counter.textContent = remaining > 0 ? formatArabicCountdown(remaining) : "دورة السحب مكتملة";
      remaining = Math.max(0, remaining - 1);
    }
    renderCountdown();
    if (remaining > 0) {
      window.setInterval(renderCountdown, 1000);
    }
  });

  const copyToast = document.querySelector("[data-copy-toast]") || document.getElementById("copyFeedback");
  let copyToastTimer = null;

  function showCopyToast(message, isError) {
    if (!copyToast) return;
    copyToast.textContent = message;
    copyToast.hidden = false;
    copyToast.classList.toggle("is-error", Boolean(isError));
    if (copyToastTimer) {
      window.clearTimeout(copyToastTimer);
    }
    copyToastTimer = window.setTimeout(function () {
      copyToast.hidden = true;
      copyToast.textContent = "";
      copyToast.classList.remove("is-error");
    }, 2600);
  }

  function copyTextValue(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text);
    }

    const scratch = document.createElement("textarea");
    scratch.value = text;
    scratch.setAttribute("readonly", "readonly");
    scratch.style.position = "fixed";
    scratch.style.opacity = "0";
    document.body.append(scratch);
    scratch.select();
    try {
      const success = document.execCommand("copy");
      scratch.remove();
      return success ? Promise.resolve() : Promise.reject(new Error("Copy failed."));
    } catch (error) {
      scratch.remove();
      return Promise.reject(error);
    }
  }

  document.querySelectorAll("[data-copy-target]").forEach(function (button) {
    button.addEventListener("click", function () {
      const target = document.querySelector(button.dataset.copyTarget || "");
      const value = target?.value || target?.textContent || "";
      if (!value.trim()) {
        showCopyToast("Nothing to copy.", true);
        return;
      }
      copyTextValue(value).then(function () {
        showCopyToast("Copied successfully");
      }).catch(function () {
        showCopyToast("Could not copy. Please select and copy manually.", true);
      });
    });
  });

  document.querySelectorAll("[data-share-message]").forEach(function (button) {
    button.addEventListener("click", function () {
      const target = document.querySelector(button.dataset.shareTarget || "");
      const text = target?.value || target?.textContent || "";
      if (!text.trim()) {
        showCopyToast("Nothing to share.", true);
        return;
      }
      if (navigator.share) {
        navigator.share({ text }).catch(function () {
          showCopyToast("Share cancelled.");
        });
        return;
      }
      copyTextValue(text).then(function () {
        showCopyToast("Copied successfully");
      }).catch(function () {
        showCopyToast("Sharing is not available here.", true);
      });
    });
  });

  document.querySelectorAll("[data-close-modal]").forEach(function (button) {
    button.addEventListener("click", function () {
      const modal = document.getElementById("introModal");
      if (!modal) return;
      modal.classList.add("closing");
      window.setTimeout(function () {
        modal.remove();
      }, 260);
    });
  });

  document.querySelectorAll("[data-user-modal-close]").forEach(function (button) {
    button.addEventListener("click", closeUserMessageModal);
  });

  userMessageModal?.addEventListener("click", function (event) {
    if (event.target === userMessageModal) {
      closeUserMessageModal();
    }
  });

  unverifiedWarningCloseButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      setUnverifiedWarningOpen(false, true);
    });
  });

  unverifiedWarningVerifyButton?.addEventListener("click", rememberUnverifiedWarningTime);

  unverifiedWarningModal?.addEventListener("click", function (event) {
    if (event.target === unverifiedWarningModal) {
      setUnverifiedWarningOpen(false, true);
    }
  });

  maybeShowUnverifiedWarning();

  verificationOpenButton?.addEventListener("click", function () {
    setVerificationModalOpen(verificationModal, true);
  });

  verificationCloseButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      setVerificationModalOpen(verificationModal, false);
    });
  });

  verificationModal?.addEventListener("click", function (event) {
    if (event.target === verificationModal) {
      setVerificationModalOpen(verificationModal, false);
    }
  });

  documentTypeSelect?.addEventListener("change", updateVerificationDocumentFields);
  updateVerificationDocumentFields();
  setupVerificationPreviews();

  if (verificationFlash) {
    setVerificationModalOpen(verificationModal, true);
    window.setTimeout(dismissVerificationFlash, 4000);
  } else if (verificationModal?.querySelector(".support-chat-error")) {
    setVerificationModalOpen(verificationModal, true);
  }

  verificationForm?.addEventListener("submit", function (event) {
    if (verificationForm.dataset.confirmed === "true") {
      return;
    }
    event.preventDefault();
    if (!verificationForm.reportValidity() || !validateVerificationFiles()) {
      return;
    }
    setVerificationModalOpen(verificationConfirmModal, true);
  });

  verificationConfirmBack?.addEventListener("click", function () {
    setVerificationModalOpen(verificationConfirmModal, false);
  });

  verificationConfirmSubmit?.addEventListener("click", function () {
    if (!verificationForm) return;
    verificationForm.dataset.confirmed = "true";
    setVerificationModalOpen(verificationConfirmModal, false);
    verificationForm.requestSubmit();
  });

  const planModal = document.querySelector("[data-plan-modal]");
  const planOpenButtons = document.querySelectorAll("[data-plan-open]");
  const planCloseButtons = document.querySelectorAll("[data-plan-close]");
  const selectedPlanInput = document.querySelector("[data-selected-plan]");
  const planTitle = document.querySelector("[data-plan-title]");
  const planAmountInput = document.querySelector("[data-plan-amount]");
  const planTransferAmount = document.querySelector("[data-plan-transfer-amount]");
  const planSwitchNotice = document.querySelector("[data-plan-switch-notice]");
  const walletAddressElement = document.querySelector("[data-wallet-address]");
  const walletCopyButton = document.querySelector("[data-wallet-copy]");
  const walletCopyStatus = document.querySelector("[data-wallet-copy-status]");
  const planProofInput = document.querySelector("[data-plan-proof]");
  const planProofPreview = document.querySelector("[data-plan-proof-preview]");
  const planProofImage = document.querySelector("[data-plan-proof-image]");
  const planProofName = document.querySelector("[data-plan-proof-name]");
  let planProofObjectUrl = "";

  if (planModal && planModal.parentElement !== body) {
    body.appendChild(planModal);
  }

  function setPlanModalOpen(isOpen) {
    if (!planModal) return;
    planModal.classList.toggle("is-open", isOpen);
    planModal.setAttribute("aria-hidden", String(!isOpen));
    body.classList.toggle("plan-modal-open", isOpen);
  }

  function planForAmount(amount) {
    if (!Number.isFinite(amount) || amount < 10) return "";
    if (amount <= 100) return "silver";
    if (amount <= 300) return "gold";
    return "vip";
  }

  function planLabel(plan) {
    return { silver: "Silver", gold: "Gold", vip: "VIP" }[plan] || plan;
  }

  function updatePlanSwitchNotice() {
    if (!selectedPlanInput || !planAmountInput || !planSwitchNotice) return;
    const amount = Number(planAmountInput.value);
    if (planTransferAmount) {
      planTransferAmount.textContent = Number.isFinite(amount) && amount > 0 ? amount.toFixed(2) : "0.00";
    }
    const finalPlan = planForAmount(amount);
    if (finalPlan && finalPlan !== selectedPlanInput.value) {
      planSwitchNotice.hidden = false;
      planSwitchNotice.textContent = `سيتم تحويل الطلب إلى ${planLabel(finalPlan)} حسب المبلغ المدخل.`;
      return;
    }
    planSwitchNotice.hidden = true;
    planSwitchNotice.textContent = "";
  }

  function clearPlanProofPreview() {
    if (planProofObjectUrl) {
      URL.revokeObjectURL(planProofObjectUrl);
      planProofObjectUrl = "";
    }
    if (planProofImage) planProofImage.src = "";
    if (planProofName) planProofName.textContent = "";
    if (planProofPreview) planProofPreview.hidden = true;
  }

  planOpenButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      const plan = button.dataset.planOpen || "silver";
      if (selectedPlanInput) selectedPlanInput.value = plan;
      if (planTitle) planTitle.textContent = button.dataset.planLabel || planLabel(plan);
      updatePlanSwitchNotice();
      setPlanModalOpen(true);
    });
  });

  planCloseButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      setPlanModalOpen(false);
    });
  });

  planModal?.addEventListener("click", function (event) {
    if (event.target === planModal) {
      setPlanModalOpen(false);
    }
  });

  planAmountInput?.addEventListener("input", updatePlanSwitchNotice);

  walletCopyButton?.addEventListener("click", function () {
    const walletAddress = walletAddressElement?.textContent?.trim() || "";
    copyTextValue(walletAddress).then(function () {
      if (walletCopyStatus) walletCopyStatus.textContent = "تم نسخ عنوان المحفظة.";
      showCopyToast("Copied successfully");
    }).catch(function () {
      if (walletCopyStatus) walletCopyStatus.textContent = "تعذر النسخ، يرجى نسخ العنوان يدوياً.";
      showCopyToast("Could not copy. Please select and copy manually.", true);
    });
  });

  planProofInput?.addEventListener("change", function () {
    clearPlanProofPreview();
    const file = planProofInput.files?.[0];
    if (!file) return;
    if (!isImageFile(file)) {
      planProofInput.value = "";
      showCopyToast("ملف الإثبات يجب أن يكون صورة.", true);
      return;
    }
    planProofObjectUrl = URL.createObjectURL(file);
    if (planProofImage) planProofImage.src = planProofObjectUrl;
    if (planProofName) planProofName.textContent = file.name;
    if (planProofPreview) planProofPreview.hidden = false;
  });

  profitWithdrawOpenButton?.addEventListener("click", function () {
    const canWithdraw = profitWithdrawOpenButton.dataset.canWithdraw === "true";
    if (!canWithdraw) {
      const message = profitWithdrawOpenButton.dataset.withdrawBlockMessage || "لا يمكن إرسال طلب السحب حالياً.";
      const status = document.querySelector("[data-withdraw-action-status]");
      if (status) status.textContent = message;
      showCopyToast(message, true);
      return;
    }
    setProfitWithdrawModalOpen(true);
  });

  profitWithdrawCloseButtons.forEach(function (button) {
    button.addEventListener("click", function () {
      setProfitWithdrawModalOpen(false);
    });
  });

  profitWithdrawModal?.addEventListener("click", function (event) {
    if (event.target === profitWithdrawModal) {
      setProfitWithdrawModalOpen(false);
    }
  });

  profitWithdrawForm?.addEventListener("submit", function (event) {
    event.preventDefault();
    const formData = new FormData(profitWithdrawForm);
    const amount = String(formData.get("amount") || "").trim();
    const walletAddress = String(formData.get("wallet_address") || "").trim();
    const network = String(formData.get("network") || "").trim();
    if (!amount || Number(amount) <= 0 || !walletAddress || !network) {
      setProfitWithdrawMessage("يرجى إدخال المبلغ وعنوان المحفظة والشبكة.", true);
      return;
    }

    pendingProfitWithdrawFormData = formData;
    if (profitWithdrawConfirmText) {
      profitWithdrawConfirmText.textContent = `هل أنت متأكد من إرسال طلب سحب أرباح بقيمة ${amount} إلى المحفظة ${walletAddress} عبر شبكة ${network}؟`;
    }
    if (profitWithdrawFields) profitWithdrawFields.hidden = true;
    if (profitWithdrawConfirm) profitWithdrawConfirm.hidden = false;
    if (profitWithdrawPrimaryActions) profitWithdrawPrimaryActions.hidden = true;
    setProfitWithdrawMessage("", false);
  });

  profitWithdrawConfirmCancel?.addEventListener("click", function () {
    pendingProfitWithdrawFormData = null;
    if (profitWithdrawFields) profitWithdrawFields.hidden = false;
    if (profitWithdrawConfirm) profitWithdrawConfirm.hidden = true;
    if (profitWithdrawPrimaryActions) profitWithdrawPrimaryActions.hidden = false;
    setProfitWithdrawMessage("", false);
  });

  profitWithdrawConfirmSubmit?.addEventListener("click", function () {
    if (!profitWithdrawForm || !pendingProfitWithdrawFormData) return;
    setProfitWithdrawLoading(true);
    fetch(profitWithdrawForm.action, {
      method: "POST",
      body: pendingProfitWithdrawFormData,
      headers: {
        "Accept": "application/json",
        "X-Requested-With": "fetch",
      },
    })
      .then(function (response) {
        return response.json().then(function (data) {
          if (!response.ok || !data.ok) {
            throw new Error(data.error || "تعذر إرسال طلب السحب.");
          }
          return data;
        });
      })
      .then(function (data) {
        setProfitWithdrawMessage(data.message || "تم إرسال طلب السحب بنجاح وسيتم مراجعته من الإدارة.", false);
        if (profitWithdrawConfirm) profitWithdrawConfirm.hidden = true;
        window.setTimeout(function () {
          window.location.reload();
        }, 1500);
      })
      .catch(function (error) {
        setProfitWithdrawMessage(error.message, true);
        if (profitWithdrawConfirm) profitWithdrawConfirm.hidden = true;
        if (profitWithdrawFields) profitWithdrawFields.hidden = false;
        if (profitWithdrawPrimaryActions) profitWithdrawPrimaryActions.hidden = false;
      })
      .finally(function () {
        setProfitWithdrawLoading(false);
      });
  });
})();
