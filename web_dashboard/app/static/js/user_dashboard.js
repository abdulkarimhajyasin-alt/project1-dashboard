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
  const verificationImageLabels = {
    front: "صورة الوجه الأمامي",
    back: "صورة الوجه الخلفي",
    passport: "صورة جواز السفر",
  };

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
  const remainingText = document.querySelector("[data-remaining-time]");
  const miningStatusLabel = document.querySelector("[data-mining-status-label]");
  const startButton = document.querySelector(".start-core-button");
  const radius = 150;
  const circumference = 2 * Math.PI * radius;

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

  if (ring) {
    const initialProgress = Number(ring.dataset.progress || 0);
    const canStart = ring.dataset.canStart === "true";
    const duration = Number(ring.dataset.duration || 86400);
    const startAt = ring.dataset.startAt ? Date.parse(ring.dataset.startAt) : 0;
    const endAt = ring.dataset.endAt ? Date.parse(ring.dataset.endAt) : 0;
    let completionChecked = false;
    let animatedProgress = 0;
    const introTimer = window.setInterval(function () {
      animatedProgress += Math.max(1, initialProgress / 24);
      if (animatedProgress >= initialProgress) {
        animatedProgress = initialProgress;
        window.clearInterval(introTimer);
      }
      setRingProgress(animatedProgress);
    }, 18);

    if (canStart) {
      countdownText.textContent = "Ready to start";
      if (remainingText) remainingText.textContent = "00:00:00";
    } else {
      window.setInterval(function () {
        const now = Date.now();
        const elapsed = startAt && endAt ? (now - startAt) / 1000 : (initialProgress / 100) * duration;
        const remaining = endAt ? (endAt - now) / 1000 : duration - elapsed;
        const liveProgress = clamp((elapsed / duration) * 100, initialProgress, 100);
        setRingProgress(liveProgress);
        const remainingLabel = formatRemaining(remaining);
        if (remainingText) remainingText.textContent = remainingLabel;
        countdownText.textContent = liveProgress >= 100 ? "Completing cycle..." : `Remaining ${remainingLabel}`;

        if (liveProgress >= 100 && !completionChecked) {
          completionChecked = true;
          fetch("/user/mining/status", { headers: { Accept: "application/json" } })
            .then(function (response) {
              return response.ok ? response.json() : null;
            })
            .then(function (data) {
              if (!data) return;
              if (data.completed) {
                countdownText.textContent = `Completed. Added $${data.completed_income}`;
                if (miningStatusLabel) miningStatusLabel.textContent = "Completed";
                if (startButton) startButton.disabled = false;
              }
            })
            .catch(function () {
              countdownText.textContent = "Cycle complete. Refresh to claim status.";
            });
        }
      }, 1000);
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

  const copyButton = document.querySelector("[data-copy-referral]");
  const copyFeedback = document.getElementById("copyFeedback");
  if (copyButton) {
    copyButton.addEventListener("click", function () {
      const input = document.getElementById("referralLink");
      if (!input) return;
      navigator.clipboard.writeText(input.value).then(function () {
        if (copyFeedback) copyFeedback.textContent = "تم نسخ الرابط";
      });
    });
  }

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
})();
