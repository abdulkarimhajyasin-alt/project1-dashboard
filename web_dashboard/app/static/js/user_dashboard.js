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
  const planSwitchNotice = document.querySelector("[data-plan-switch-notice]");
  const walletInput = document.querySelector("[data-wallet-address]");
  const walletCopyButton = document.querySelector("[data-wallet-copy]");
  const walletCopyStatus = document.querySelector("[data-wallet-copy-status]");
  const planProofInput = document.querySelector("[data-plan-proof]");
  const planProofPreview = document.querySelector("[data-plan-proof-preview]");
  const planProofImage = document.querySelector("[data-plan-proof-image]");
  const planProofName = document.querySelector("[data-plan-proof-name]");
  let planProofObjectUrl = "";

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
    const walletAddress = walletInput?.value || "";
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
})();
