(() => {
  const body = document.body;
  const drawer = document.querySelector("[data-admin-drawer]");
  const overlay = document.querySelector("[data-drawer-overlay]");
  const openButtons = Array.from(document.querySelectorAll("[data-drawer-open]"));
  const closeButtons = Array.from(document.querySelectorAll("[data-drawer-close]"));
  const notificationRoots = Array.from(document.querySelectorAll("[data-notification-root]"));
  const supportChatModal = document.querySelector("[data-support-chat-modal]");
  const supportChatOpenButtons = Array.from(document.querySelectorAll("[data-support-chat-open]"));
  const supportChatCloseButtons = Array.from(document.querySelectorAll("[data-support-chat-close]"));
  const supportFileInputs = Array.from(document.querySelectorAll("[data-support-file-input]"));
  const adminModalOpenButtons = Array.from(document.querySelectorAll("[data-admin-modal-open]"));
  const adminModals = Array.from(document.querySelectorAll("[data-admin-modal]"));
  const adminImageButtons = Array.from(document.querySelectorAll("[data-admin-image-src]"));
  const deleteUserModal = document.querySelector("[data-delete-user-modal]");
  const deleteUserName = deleteUserModal?.querySelector("[data-delete-user-name]");
  const deleteUserConfirm = deleteUserModal?.querySelector("[data-delete-user-confirm]");
  const deleteUserError = deleteUserModal?.querySelector("[data-delete-user-error]");
  const deleteUserCancelButtons = Array.from(deleteUserModal?.querySelectorAll("[data-delete-user-cancel]") || []);
  const activeMiningOpen = document.querySelector("[data-active-mining-open]");
  const activeMiningModal = document.querySelector("[data-active-mining-modal]");
  const activeMiningState = activeMiningModal?.querySelector("[data-active-mining-state]");
  const activeMiningList = activeMiningModal?.querySelector("[data-active-mining-list]");
  const activeMiningCount = document.querySelector("[data-active-mining-count]");
  const imageExtensions = [".gif", ".jpeg", ".jpg", ".png", ".webp"];
  let pendingDeleteUserForm = null;

  const formatFileSize = (size) => {
    if (!Number.isFinite(size)) {
      return "";
    }
    if (size < 1024 * 1024) {
      return `${Math.max(1, Math.round(size / 1024))} KB`;
    }
    return `${(size / (1024 * 1024)).toFixed(1)} MB`;
  };

  const isImageFile = (file) => {
    const fileName = (file.name || "").toLowerCase();
    return file.type.startsWith("image/") || imageExtensions.some((extension) => fileName.endsWith(extension));
  };

  const setupSupportFilePreview = () => {
    supportFileInputs.forEach((input) => {
      const form = input.closest("form");
      const preview = form?.querySelector("[data-support-file-preview]");
      const image = form?.querySelector("[data-support-file-preview-image]");
      const icon = form?.querySelector("[data-support-file-preview-icon]");
      const name = form?.querySelector("[data-support-file-preview-name]");
      const meta = form?.querySelector("[data-support-file-preview-meta]");
      const clearButton = form?.querySelector("[data-support-file-clear]");
      let objectUrl = "";

      if (!preview || !image || !icon || !name || !meta || !clearButton) {
        return;
      }

      const resetPreview = () => {
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
      };

      input.addEventListener("change", () => {
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
      form?.addEventListener("submit", () => {
        if (objectUrl) {
          URL.revokeObjectURL(objectUrl);
        }
      });
    });
  };

  const setSupportChatOpen = (isOpen) => {
    if (!supportChatModal) {
      return;
    }

    supportChatModal.classList.toggle("is-open", isOpen);
    supportChatModal.setAttribute("aria-hidden", String(!isOpen));
    document.body.classList.toggle("support-chat-open", isOpen);
  };

  const setAdminModalOpen = (modal, isOpen) => {
    if (!modal) {
      return;
    }

    modal.classList.toggle("is-open", isOpen);
    modal.setAttribute("aria-hidden", String(!isOpen));
    document.body.classList.toggle(
      "admin-modal-open",
      adminModals.some((item) => item.classList.contains("is-open")) || Boolean(deleteUserModal?.classList.contains("is-open")),
    );
  };

  const setDeleteUserModalOpen = (isOpen) => {
    if (!deleteUserModal) {
      return;
    }

    deleteUserModal.classList.toggle("is-open", isOpen);
    deleteUserModal.setAttribute("aria-hidden", String(!isOpen));
    document.body.classList.toggle(
      "admin-modal-open",
      isOpen || adminModals.some((item) => item.classList.contains("is-open")),
    );

    if (!isOpen) {
      pendingDeleteUserForm = null;
      if (deleteUserConfirm) {
        deleteUserConfirm.disabled = false;
        deleteUserConfirm.textContent = "Confirm Delete";
      }
      if (deleteUserError) {
        deleteUserError.hidden = true;
        deleteUserError.textContent = "";
      }
    }
  };

  const setActiveMiningState = (message, type = "loading") => {
    if (!activeMiningState) {
      return;
    }
    activeMiningState.hidden = !message;
    activeMiningState.textContent = message || "";
    activeMiningState.dataset.state = type;
  };

  const makeActiveCycleMetric = (label, value) => {
    const item = document.createElement("div");
    item.className = "active-cycle-metric";

    const labelNode = document.createElement("span");
    labelNode.textContent = label;

    const valueNode = document.createElement("strong");
    valueNode.textContent = value || "-";

    item.append(labelNode, valueNode);
    return item;
  };

  const makeActiveCycleCard = (cycle) => {
    const card = document.createElement("article");
    card.className = "active-cycle-user-card";

    const header = document.createElement("div");
    header.className = "active-cycle-card-header";

    const titleGroup = document.createElement("div");
    const title = document.createElement("h3");
    title.textContent = cycle.name || "-";
    const meta = document.createElement("p");
    meta.textContent = `${cycle.username || "-"} • ${cycle.email || "-"}`;
    titleGroup.append(title, meta);

    const details = document.createElement("a");
    details.className = "admin-user-link active-cycle-details";
    details.href = cycle.detail_url || `/users/${cycle.user_id}`;
    details.textContent = "Details";

    header.append(titleGroup, details);

    const metrics = document.createElement("div");
    metrics.className = "active-cycle-metrics";
    [
      ["Active Capital", `$${cycle.active_capital || "0.00"}`],
      ["Current Daily Income", `$${cycle.current_daily_income || "0.0000"}`],
      ["Expected Earned Income", `$${cycle.expected_earned_income || "0.0000"}`],
      ["Cycle Start Time", cycle.cycle_start_time],
      ["Actual Start Time", cycle.actual_start_time],
      ["End Time", cycle.end_time],
      ["Remaining Time", cycle.remaining_time],
      ["Missed Time", cycle.missed_time],
      ["Timezone", cycle.timezone],
    ].forEach(([label, value]) => metrics.append(makeActiveCycleMetric(label, value)));

    const progressValue = Number.parseFloat(cycle.progress_percent ?? 0);
    const progressText = Number.isFinite(progressValue) ? progressValue.toFixed(2) : "0.00";
    const progress = document.createElement("div");
    progress.className = "active-cycle-progress";
    progress.innerHTML = `
      <div class="active-cycle-progress-label">
        <span>Progress</span>
        <strong>${progressText}%</strong>
      </div>
      <div class="active-cycle-progress-track">
        <span style="width: ${progressText}%"></span>
      </div>
    `;

    card.append(header, metrics, progress);
    return card;
  };

  const renderActiveMiningCycles = (cycles) => {
    if (!activeMiningList) {
      return;
    }

    activeMiningList.innerHTML = "";
    if (!Array.isArray(cycles) || cycles.length === 0) {
      setActiveMiningState("No active mining cycles.", "empty");
      return;
    }

    setActiveMiningState("", "ready");
    cycles.forEach((cycle) => activeMiningList.append(makeActiveCycleCard(cycle)));
  };

  const loadActiveMiningCycles = async () => {
    if (!activeMiningModal || !activeMiningList) {
      return;
    }

    setAdminModalOpen(activeMiningModal, true);
    setActiveMiningState("Loading active mining cycles...", "loading");
    activeMiningList.innerHTML = "";
    if (activeMiningOpen) {
      activeMiningOpen.disabled = true;
    }

    try {
      const response = await fetch("/dashboard/active-mining-cycles", {
        credentials: "same-origin",
        headers: { Accept: "application/json" },
      });
      if (!response.ok) {
        throw new Error("Unable to load active mining cycles.");
      }
      const data = await response.json();
      if (activeMiningCount) {
        activeMiningCount.textContent = String(data.count ?? 0);
      }
      renderActiveMiningCycles(data.cycles || []);
    } catch (error) {
      setActiveMiningState(error.message || "Unable to load active mining cycles.", "error");
    } finally {
      if (activeMiningOpen) {
        activeMiningOpen.disabled = false;
      }
    }
  };

  document.addEventListener("submit", (event) => {
    const form = event.target.closest("[data-delete-user-form]");
    if (!form) {
      return;
    }
    if (form.dataset.deleteConfirmed === "true") {
      return;
    }

    event.preventDefault();

    if (form.dataset.deleteProtected === "true") {
      if (deleteUserError) {
        deleteUserError.hidden = false;
        deleteUserError.textContent = "Main admin account cannot be deleted.";
      }
      return;
    }

    pendingDeleteUserForm = form;
    if (deleteUserName) {
      deleteUserName.textContent = form.dataset.userName || "this user";
    }
    if (deleteUserError) {
      deleteUserError.hidden = true;
      deleteUserError.textContent = "";
    }
    if (deleteUserConfirm) {
      deleteUserConfirm.disabled = false;
      deleteUserConfirm.textContent = "Confirm Delete";
    }
    setDeleteUserModalOpen(true);
  });

  deleteUserConfirm?.addEventListener("click", () => {
    if (!pendingDeleteUserForm || pendingDeleteUserForm.dataset.deleteProtected === "true") {
      if (deleteUserError) {
        deleteUserError.hidden = false;
        deleteUserError.textContent = "This user cannot be deleted.";
      }
      return;
    }

    deleteUserConfirm.disabled = true;
    deleteUserConfirm.textContent = "Deleting...";
    pendingDeleteUserForm.dataset.deleteConfirmed = "true";

    if (typeof pendingDeleteUserForm.requestSubmit === "function") {
      pendingDeleteUserForm.requestSubmit();
    } else {
      pendingDeleteUserForm.submit();
    }
  });

  deleteUserCancelButtons.forEach((button) => {
    button.addEventListener("click", () => {
      if (!deleteUserConfirm?.disabled) {
        setDeleteUserModalOpen(false);
      }
    });
  });

  deleteUserModal?.addEventListener("click", (event) => {
    if (event.target === deleteUserModal && !deleteUserConfirm?.disabled) {
      setDeleteUserModalOpen(false);
    }
  });

  adminModalOpenButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const modal = document.getElementById(button.dataset.adminModalOpen);
      setAdminModalOpen(modal, true);
    });
  });

  adminModals.forEach((modal) => {
    modal.querySelectorAll("[data-admin-modal-close]").forEach((button) => {
      button.addEventListener("click", () => setAdminModalOpen(modal, false));
    });
    modal.addEventListener("click", (event) => {
      if (event.target === modal) {
        setAdminModalOpen(modal, false);
      }
    });
  });

  activeMiningOpen?.addEventListener("click", loadActiveMiningCycles);

  const userDetailTabs = document.querySelector("[data-admin-user-detail-tabs]");
  if (userDetailTabs) {
    const tabLinks = Array.from(userDetailTabs.querySelectorAll("[data-admin-detail-tab]"));
    const tabPanels = Array.from(userDetailTabs.querySelectorAll("[data-admin-detail-panel]"));
    const panelIds = new Set(tabPanels.map((panel) => panel.dataset.adminDetailPanel));

    const activateUserDetailTab = (target, shouldPushState = true) => {
      const nextTarget = panelIds.has(target) ? target : "overview";
      tabLinks.forEach((link) => {
        const isActive = link.dataset.adminDetailTab === nextTarget;
        link.classList.toggle("is-primary", isActive);
        link.setAttribute("aria-selected", String(isActive));
      });
      tabPanels.forEach((panel) => {
        panel.hidden = panel.dataset.adminDetailPanel !== nextTarget;
      });
      const nextHash = `#${nextTarget}`;
      if (shouldPushState && window.location.hash !== nextHash) {
        window.history.pushState({ userDetailTab: nextTarget }, "", nextHash);
      }
    };

    tabLinks.forEach((link) => {
      link.addEventListener("click", (event) => {
        event.preventDefault();
        activateUserDetailTab(link.dataset.adminDetailTab || "overview");
      });
    });

    activateUserDetailTab((window.location.hash || "#overview").slice(1), false);
    window.addEventListener("popstate", () => {
      activateUserDetailTab((window.location.hash || "#overview").slice(1), false);
    });
  }

  adminImageButtons.forEach((button) => {
    button.addEventListener("click", () => {
      const modal = document.getElementById("verificationImagePreview");
      const image = modal?.querySelector("[data-admin-image-preview]");
      const title = modal?.querySelector("[data-admin-image-title]");
      if (!modal || !image) {
        return;
      }
      image.src = button.dataset.adminImageSrc || "";
      if (title) {
        title.textContent = button.dataset.adminImageTitle || "صورة التوثيق";
      }
      setAdminModalOpen(modal, true);
    });
  });

  supportChatOpenButtons.forEach((button) => {
    button.addEventListener("click", () => setSupportChatOpen(true));
  });

  supportChatCloseButtons.forEach((button) => {
    button.addEventListener("click", () => setSupportChatOpen(false));
  });

  supportChatModal?.addEventListener("click", (event) => {
    if (event.target === supportChatModal) {
      setSupportChatOpen(false);
    }
  });

  const closeNotifications = (exceptRoot = null) => {
    notificationRoots.forEach((root) => {
      if (root === exceptRoot) {
        return;
      }

      root.classList.remove("is-open");
      root.querySelector("[data-notification-toggle]")?.setAttribute("aria-expanded", "false");
      root.querySelector("[data-notification-panel]")?.setAttribute("aria-hidden", "true");
    });
  };

  notificationRoots.forEach((root) => {
    const toggle = root.querySelector("[data-notification-toggle]");
    const panel = root.querySelector("[data-notification-panel]");

    toggle?.addEventListener("click", (event) => {
      event.stopPropagation();
      const isOpen = !root.classList.contains("is-open");
      closeNotifications(root);
      root.classList.toggle("is-open", isOpen);
      toggle.setAttribute("aria-expanded", String(isOpen));
      panel?.setAttribute("aria-hidden", String(!isOpen));
    });
  });

  const realtimeToast = (() => {
    const toast = document.createElement("div");
    toast.className = "realtime-toast";
    toast.hidden = true;
    document.body.append(toast);
    let timer = null;
    return (message) => {
      toast.textContent = message;
      toast.hidden = false;
      window.clearTimeout(timer);
      timer = window.setTimeout(() => {
        toast.hidden = true;
      }, 3200);
    };
  })();

  const escapeHtml = (value = "") => String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  }[char]));

  const latestNotificationIdFromDom = () => {
    const first = document.querySelector(".notification-item[href*='/open']");
    const match = first?.getAttribute("href")?.match(/\/(\d+)\/open/);
    return match ? Number(match[1]) : 0;
  };

  let latestRealtimeNotificationId = latestNotificationIdFromDom();
  let notificationPollTimer = null;
  let notificationPollInFlight = false;

  const renderNotifications = (payload) => {
    notificationRoots.forEach((root) => {
      const count = Number(payload.unread_count || 0);
      const bell = root.querySelector("[data-notification-toggle]");
      const oldBadge = root.querySelector(".notification-badge");
      oldBadge?.remove();
      if (count > 0 && bell) {
        const badge = document.createElement("span");
        badge.className = "notification-badge";
        badge.textContent = String(count);
        bell.append(badge);
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
      list.innerHTML = notifications.map((item) => `
        <a class="notification-item ${escapeHtml(item.kind || "system")}" href="${escapeHtml(item.open_url || "/notifications")}">
          <strong>${escapeHtml(item.title)}</strong>
          <p>${escapeHtml(item.message)}</p>
          <small>${escapeHtml(item.created_label || "")}</small>
        </a>
      `).join("");
    });
  };

  const renderSupportMessages = (messages) => {
    const bodyEl = supportChatModal?.querySelector("[data-support-chat-body]");
    if (!bodyEl || !Array.isArray(messages)) return;
    const previousLast = Number(bodyEl.querySelector("[data-support-message-id]:last-child")?.dataset.supportMessageId || 0);
    bodyEl.innerHTML = messages.map((message) => `
      <article class="support-bubble ${message.sender_type === "admin" ? "from-admin" : "from-user"}" data-support-message-id="${message.id}">
        <div class="support-bubble-meta">
          <strong>${escapeHtml(message.sender_label || "")}</strong>
          <small>${escapeHtml(message.created_label || "")}</small>
        </div>
        ${message.body ? `<p>${escapeHtml(message.body)}</p>` : ""}
        ${message.has_attachment ? (message.is_image ? `<img src="${escapeHtml(message.attachment_url)}" class="chat-image" alt="attachment">` : `<a href="${escapeHtml(message.attachment_url)}">تحميل الملف</a>`) : ""}
      </article>
    `).join("") || '<div class="support-chat-empty"><strong>لا توجد رسائل بعد</strong><p>ابدأ المحادثة برسالة واضحة.</p></div>';
    const nextLast = Number(messages[messages.length - 1]?.id || 0);
    if (nextLast > previousLast) bodyEl.scrollTop = bodyEl.scrollHeight;
  };

  const pollNotifications = (forceToast = false) => {
    if (notificationPollInFlight) return Promise.resolve();
    notificationPollInFlight = true;
    const threadId = supportChatModal?.classList.contains("is-open") ? supportChatModal.dataset.supportThreadId : "";
    const query = threadId ? `?thread_id=${encodeURIComponent(threadId)}` : "";
    return fetch(`/dashboard/notifications/poll${query}`, {
      credentials: "same-origin",
      headers: { Accept: "application/json" },
    })
      .then((response) => (response.ok ? response.json() : null))
      .then((payload) => {
        if (!payload) return;
        renderNotifications(payload);
        const latest = Number(payload.latest_notification_id || 0);
        if (latest > latestRealtimeNotificationId && (latestRealtimeNotificationId || forceToast)) {
          realtimeToast(payload.notifications?.[0]?.title || "New notification");
        }
        latestRealtimeNotificationId = Math.max(latestRealtimeNotificationId, latest);
      })
      .finally(() => {
        notificationPollInFlight = false;
      });
  };

  const scheduleNotificationPoll = () => {
    window.clearTimeout(notificationPollTimer);
    const delay = document.hidden ? 15000 : 3000;
    notificationPollTimer = window.setTimeout(() => {
      pollNotifications().finally(scheduleNotificationPoll);
    }, delay);
  };

  if (!window.__novaAdminNotificationPollingStarted) {
    window.__novaAdminNotificationPollingStarted = true;
    scheduleNotificationPoll();
    document.addEventListener("visibilitychange", () => {
      if (!document.hidden) pollNotifications(true);
      scheduleNotificationPoll();
    });
    window.addEventListener("beforeunload", () => window.clearTimeout(notificationPollTimer));
  }

  document.addEventListener("click", (event) => {
    const notificationLink = event.target.closest(".notification-item[href*='/open']");
    if (!notificationLink) return;
    const badge = notificationLink.closest("[data-notification-root]")?.querySelector(".notification-badge");
    if (badge) {
      const next = Math.max(0, Number(badge.textContent || 0) - 1);
      badge.textContent = String(next);
      if (!next) badge.remove();
    }
  });

  notificationRoots.forEach((root) => {
    const clearForm = root.querySelector("[data-notification-clear-form]");
    clearForm?.addEventListener("submit", (event) => {
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
        .then((response) => (response.ok ? response.json() : Promise.reject(new Error("تعذر مسح الإشعارات."))))
        .then((payload) => {
          renderNotifications(payload);
          latestRealtimeNotificationId = Number(payload.latest_notification_id || 0);
        })
        .catch((error) => {
          realtimeToast(error.message || "تعذر مسح الإشعارات.");
          if (button) button.disabled = false;
        });
    });
  });

  supportChatModal?.querySelector("[data-support-compose]")?.addEventListener("submit", (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector("button[type='submit']");
    button.disabled = true;
    fetch(form.action, {
      method: "POST",
      body: new FormData(form),
      credentials: "same-origin",
      headers: { "X-Requested-With": "fetch", Accept: "application/json" },
    })
      .then((response) => response.json().then((data) => ({ ok: response.ok, data })))
      .then(({ ok, data }) => {
        if (!ok || data.ok === false) throw new Error(data.error || "Could not send message.");
        form.reset();
        form.querySelector("[data-support-file-clear]")?.click();
        renderSupportMessages(data.messages || (data.message ? [data.message] : []));
        pollNotifications(true);
      })
      .catch((error) => realtimeToast(error.message || "Could not send message."))
      .finally(() => {
        button.disabled = false;
      });
  });

  const setDrawerOpen = (isOpen) => {
    if (!drawer) {
      return;
    }

    body.classList.remove("admin-drawer-open");
    body.classList.toggle("menu-open", isOpen);
    drawer.classList.toggle("is-open", isOpen);
    overlay?.classList.toggle("is-visible", isOpen);
    drawer.setAttribute("aria-hidden", String(!isOpen));
    overlay?.setAttribute("aria-hidden", String(!isOpen));
    openButtons.forEach((button) => {
      button.setAttribute("aria-expanded", String(isOpen));
    });
  };

  openButtons.forEach((button) => {
    button.addEventListener("click", () => setDrawerOpen(true));
  });

  closeButtons.forEach((button) => {
    button.addEventListener("click", () => setDrawerOpen(false));
  });

  overlay?.addEventListener("click", () => setDrawerOpen(false));

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      setDrawerOpen(false);
      closeNotifications();
      setSupportChatOpen(false);
      adminModals.forEach((modal) => setAdminModalOpen(modal, false));
      if (!deleteUserConfirm?.disabled) {
        setDeleteUserModalOpen(false);
      }
    }
  });

  document.addEventListener("click", (event) => {
    if (!event.target.closest("[data-notification-root]")) {
      closeNotifications();
    }
  });

  setDrawerOpen(false);
  closeNotifications();
  setupSupportFilePreview();
  setSupportChatOpen(supportChatModal?.classList.contains("is-open") || false);

  const referralTree = document.querySelector("[data-referral-tree]");

  if (referralTree) {
    const childrenCache = new Map();
    const expandedNodes = new Set();

    const makePostActionForm = (action, buttonClass, label) => {
      const form = document.createElement("form");
      form.method = "post";
      form.action = action;

      const button = document.createElement("button");
      button.className = buttonClass;
      button.type = "submit";
      button.textContent = label;
      form.append(button);
      return form;
    };

    const makeDeleteForm = (user) => {
      const form = makePostActionForm(user.delete_url || `/users/${user.id}/delete`, "admin-user-action danger compact", "Delete");
      form.dataset.deleteUserForm = "";
      form.dataset.userName = user.delete_label || user.username || user.name || "this user";
      form.dataset.deleteProtected = user.delete_protected ? "true" : "false";

      const hidden = document.createElement("input");
      hidden.type = "hidden";
      hidden.name = "confirm_delete";
      hidden.value = "yes";
      form.prepend(hidden);

      const button = form.querySelector("button");
      if (button && user.delete_protected) {
        button.disabled = true;
        button.title = "Main admin account cannot be deleted";
      }
      return form;
    };

    const setToggleState = (button, isExpanded) => {
      if (!button) {
        return;
      }
      button.textContent = isExpanded ? "Hide" : "View";
      button.setAttribute("aria-expanded", String(isExpanded));
    };

    const setToggleLoading = (button, isLoading) => {
      if (!button) {
        return;
      }
      button.disabled = isLoading;
      button.textContent = isLoading ? "Loading..." : "View";
    };

    const tableBody = referralTree.querySelector(".admin-users-table tbody");
    const referralDebug = (...args) => console.debug("[referral-tree]", ...args);

    const formatMoney = (value, digits) => {
      const amount = Number.parseFloat(value ?? 0);
      return `$${(Number.isFinite(amount) ? amount : 0).toFixed(digits)}`;
    };

    const hasAncestor = (row, userId) => (row.dataset.ancestorIds || "").split(",").includes(String(userId));

    const getDescendantRows = (userId) => Array.from(
      tableBody?.querySelectorAll("[data-user-row], [data-referral-feedback-row]") || [],
    ).filter((row) => hasAncestor(row, userId));

    const getInsertionAnchor = (parentRow, userId) => {
      const descendants = getDescendantRows(userId);
      return descendants.length ? descendants[descendants.length - 1] : parentRow;
    };

    const insertRowsAfter = (parentRow, userId, rows) => {
      if (!tableBody || !parentRow || !rows.length) {
        referralDebug("insert skipped", {
          hasTbody: Boolean(tableBody),
          hasParentRow: Boolean(parentRow),
          rows: rows.length,
          userId,
        });
        return false;
      }

      let anchor = getInsertionAnchor(parentRow, userId);
      rows.forEach((row) => {
        tableBody.insertBefore(row, anchor.nextSibling);
        anchor = row;
      });

      const inserted = rows.every((row) => row.isConnected && row.parentElement === tableBody);
      referralDebug("row insertion", {
        userId,
        requested: rows.length,
        inserted,
        tbodyRows: tableBody.querySelectorAll("tr").length,
      });
      return inserted;
    };

    const removeDescendantRows = (parentRow, userId) => {
      getDescendantRows(userId).forEach((row) => {
        if (row.dataset.userId) {
          expandedNodes.delete(row.dataset.userId);
        }
        row.remove();
      });
      expandedNodes.delete(String(userId));
      parentRow?.querySelectorAll("[data-referral-toggle]").forEach((toggle) => {
        if (toggle.dataset.userId !== String(userId) && expandedNodes.has(toggle.dataset.userId)) {
          setToggleState(toggle, false);
        }
      });
    };

    const makeFeedback = (message, type = "loading") => {
      const row = document.createElement("tr");
      row.className = `admin-users-table-row referral-feedback-row referral-${type}`;
      row.dataset.referralFeedbackRow = "";
      const cell = document.createElement("td");
      cell.colSpan = 11;
      const item = document.createElement("div");
      item.className = `referral-feedback referral-${type}`;
      if (type === "loading") {
        item.innerHTML = "<span></span><span></span><span></span>";
      } else {
        item.textContent = message;
      }
      cell.append(item);
      row.append(cell);
      return row;
    };

    const makeBadge = (text, className = "") => {
      const badge = document.createElement("span");
      badge.className = `user-badge ${className}`.trim();
      badge.textContent = text;
      return badge;
    };

    const makeTableCell = (label, content) => {
      const cell = document.createElement("td");
      cell.dataset.label = label;
      if (content instanceof Node) {
        cell.append(content);
      } else {
        cell.textContent = content;
      }
      return cell;
    };

    const makeChildRow = (user, level, ancestorIds) => {
      const row = document.createElement("tr");
      row.className = "admin-users-table-row referral-table-child-row";
      row.dataset.userRow = "";
      row.dataset.userId = String(user.id);
      row.dataset.treeLevel = String(level);
      row.dataset.ancestorIds = ancestorIds.join(",");
      row.style.setProperty("--tree-indent", `${Math.min(level, 8) * 18}px`);

      const usernameWrap = document.createElement("div");
      usernameWrap.className = "referral-tree-user";
      const userLink = document.createElement("a");
      userLink.className = "admin-users-username";
      userLink.href = user.detail_url || `/users/${user.id}`;
      userLink.textContent = user.username || user.name || "-";
      usernameWrap.append(userLink, makeBadge(`Level ${level}`, "tree-level"));

      const nameLink = document.createElement("a");
      nameLink.className = "admin-users-name-link";
      nameLink.href = user.detail_url || `/users/${user.id}`;
      nameLink.textContent = user.name || "-";

      const plan = makeBadge((user.plan || "none").toUpperCase(), "plan");
      const status = makeBadge(user.status || "active", `status-${user.status || "active"}`);
      const verified = makeBadge(user.verified ? "Verified" : "Not verified", user.verified ? "is-verified" : "is-muted");
      const childrenCount = Number(user.children_count || user.referrals_count || 0);
      const children = document.createElement("div");
      children.className = "admin-users-children-cell";
      children.append(makeBadge(String(childrenCount), "children"));

      const actions = document.createElement("div");
      actions.className = "admin-users-action-cell";
      const view = document.createElement("button");
      view.type = "button";
      view.className = "admin-user-action primary compact";
      view.dataset.referralToggle = "";
      view.dataset.userId = String(user.id);
      view.dataset.treeLevel = String(level);
      view.dataset.childrenCount = String(childrenCount);
      view.setAttribute("aria-expanded", "false");
      view.textContent = "View";
      if (!childrenCount) {
        view.disabled = true;
        view.title = "No children for this user";
      }
      const reset = document.createElement("button");
      reset.type = "button";
      reset.className = "admin-user-action safe compact";
      reset.textContent = "Reset";
      actions.append(
        view,
        makePostActionForm(user.message_url || `/users/${user.id}/message`, "admin-user-action success compact", "Message"),
        reset,
        makeDeleteForm(user),
      );

      const balance = Number.parseFloat(user.capital ?? 0) + Number.parseFloat(user.profits ?? 0);
      row.append(
        makeTableCell("Username", usernameWrap),
        makeTableCell("Name", nameLink),
        makeTableCell("Country", user.country || "-"),
        makeTableCell("Plan", plan),
        makeTableCell("Status", status),
        makeTableCell("Verified", verified),
        makeTableCell("Capital", formatMoney(user.capital, 2)),
        makeTableCell("Balance", formatMoney(balance, 4)),
        makeTableCell("Profit", formatMoney(user.profits, 4)),
        makeTableCell("Children", children),
        makeTableCell("Action", actions),
      );
      return row;
    };

    const renderChildren = (parentCard, parentId, children) => {
      removeDescendantRows(parentCard, parentId);

      const parentAncestors = (parentCard.dataset.ancestorIds || "").split(",").filter(Boolean);
      const ancestorIds = [...parentAncestors, String(parentId)];
      const level = Number(parentCard.dataset.treeLevel || 0) + 1;
      const rows = [];

      if (!children.length) {
        const emptyRow = makeFeedback("No children found.", "empty");
        emptyRow.dataset.ancestorIds = ancestorIds.join(",");
        rows.push(emptyRow);
      } else {
        children.forEach((child) => {
          rows.push(makeChildRow(child, level, ancestorIds));
        });
      }

      const inserted = insertRowsAfter(parentCard, parentId, rows);
      if (inserted) {
        expandedNodes.add(String(parentId));
        setToggleState(parentCard.querySelector(`[data-referral-toggle][data-user-id="${parentId}"]`), true);
      }
      return inserted;
    };

    referralTree.addEventListener("click", (event) => {
      const button = event.target.closest("[data-referral-toggle]");
      if (!button || !referralTree.contains(button)) {
        return;
      }

      const parentCard = button.closest("[data-user-row]");
      const userId = button.dataset.userId;

      referralDebug("toggle click", {
        userId,
        hasTbody: Boolean(tableBody),
        parentRowFound: Boolean(parentCard),
        expanded: expandedNodes.has(userId),
      });

      if (!parentCard || !userId) {
        return;
      }

      if (expandedNodes.has(userId)) {
        removeDescendantRows(parentCard, userId);
        setToggleState(button, false);
        return;
      }

      if (childrenCache.has(userId)) {
        const cachedChildren = childrenCache.get(userId);
        referralDebug("cache hit", { userId, childrenCount: cachedChildren.length });
        renderChildren(parentCard, userId, cachedChildren);
        return;
      }

      removeDescendantRows(parentCard, userId);
      const loadingRow = makeFeedback("Loading children...", "loading");
      const parentAncestors = (parentCard.dataset.ancestorIds || "").split(",").filter(Boolean);
      loadingRow.dataset.ancestorIds = [...parentAncestors, String(userId)].join(",");
      insertRowsAfter(parentCard, userId, [loadingRow]);
      setToggleLoading(button, true);

      fetch(`/users/${userId}/children`, {
        credentials: "same-origin",
        headers: { Accept: "application/json" },
      })
        .then((response) => {
          referralDebug("fetch response", { userId, status: response.status, ok: response.ok });
          if (!response.ok) {
            throw new Error("Could not load children.");
          }
          return response.json();
        })
        .then((data) => {
          const children = Array.isArray(data) ? data : (Array.isArray(data.children) ? data.children : []);
          referralDebug("response payload", {
            userId,
            schema: Array.isArray(data) ? "array" : typeof data,
            hasChildrenKey: Object.prototype.hasOwnProperty.call(data || {}, "children"),
            childrenCount: children.length,
          });
          childrenCache.set(userId, children);
          loadingRow.remove();
          setToggleLoading(button, false);
          if (!renderChildren(parentCard, userId, children)) {
            throw new Error("Could not insert child rows.");
          }
        })
        .catch((error) => {
          referralDebug("error", { userId, message: error.message || String(error) });
          loadingRow.remove();
          setToggleLoading(button, false);
          const errorRow = makeFeedback(error.message || "Could not load children.", "error");
          errorRow.dataset.ancestorIds = loadingRow.dataset.ancestorIds || String(userId);
          insertRowsAfter(parentCard, userId, [errorRow]);
        });
    });
  }

  const dashboard = document.querySelector("[data-dashboard-page]");

  if (!dashboard) {
    return;
  }

  const sections = Array.from(dashboard.querySelectorAll("[data-section]"));
  const sectionMap = new Map(sections.map((section) => [section.dataset.section, section]));
  const targetLinks = Array.from(document.querySelectorAll("[data-target]"));
  const navLinks = targetLinks.filter((link) => link.closest("[data-dashboard-nav]"));
  const heading = document.querySelector("[data-dashboard-heading]");
  const subtitle = document.querySelector("[data-dashboard-subtitle]");

  const getTargetFromHash = () => window.location.hash.replace("#", "") || "home";

  const setActiveSection = (target, shouldPushState = true) => {
    const nextTarget = sectionMap.has(target) ? target : "home";
    const nextSection = sectionMap.get(nextTarget);

    sections.forEach((section) => {
      const isActive = section === nextSection;
      section.hidden = !isActive;
      section.classList.toggle("is-active", isActive);
      section.setAttribute("aria-hidden", String(!isActive));
    });

    navLinks.forEach((link) => {
      const isActive = link.dataset.target === nextTarget;
      link.classList.toggle("active", isActive);
      link.setAttribute("aria-current", isActive ? "page" : "false");
    });

    if (heading && nextSection.dataset.title) {
      heading.textContent = nextSection.dataset.title;
    }

    if (subtitle && nextSection.dataset.description) {
      subtitle.textContent = nextSection.dataset.description;
    }

    const nextHash = `#${nextTarget}`;
    if (shouldPushState && window.location.hash !== nextHash) {
      window.history.pushState({ section: nextTarget }, "", nextHash);
    }
  };

  targetLinks.forEach((link) => {
    link.addEventListener("click", (event) => {
      const target = link.dataset.target;

      if (!sectionMap.has(target)) {
        return;
      }

      event.preventDefault();
      setActiveSection(target);
      setDrawerOpen(false);
    });
  });

  window.addEventListener("popstate", () => {
    setActiveSection(getTargetFromHash(), false);
  });

  setActiveSection(getTargetFromHash(), false);
})();
