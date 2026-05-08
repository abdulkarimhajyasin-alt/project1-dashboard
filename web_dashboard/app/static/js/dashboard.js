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
  const supportImageLightbox = document.querySelector("[data-support-image-lightbox]");
  const supportImagePreview = document.querySelector("[data-support-image-preview]");
  const supportImageTitle = document.querySelector("[data-support-image-title]");
  const supportImageOpenButtons = Array.from(document.querySelectorAll("[data-support-image-open]"));
  const supportImageCloseButtons = Array.from(document.querySelectorAll("[data-support-image-close]"));
  const supportFileInputs = Array.from(document.querySelectorAll("[data-support-file-input]"));
  const imageExtensions = [".apng", ".avif", ".bmp", ".gif", ".jpeg", ".jpg", ".png", ".svg", ".webp"];

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

  const setSupportImageOpen = (isOpen, src = "", title = "") => {
    if (!supportImageLightbox || !supportImagePreview) {
      return;
    }

    supportImageLightbox.classList.toggle("is-open", isOpen);
    supportImageLightbox.setAttribute("aria-hidden", String(!isOpen));
    body.classList.toggle("support-image-open", isOpen);

    if (isOpen) {
      supportImagePreview.src = src;
      supportImagePreview.alt = title || "صورة مرفقة";
      if (supportImageTitle) {
        supportImageTitle.textContent = title || "صورة مرفقة";
      }
    } else {
      supportImagePreview.src = "";
      supportImagePreview.alt = "";
      if (supportImageTitle) {
        supportImageTitle.textContent = "";
      }
    }
  };

  const setSupportChatOpen = (isOpen) => {
    if (!supportChatModal) {
      return;
    }

    supportChatModal.classList.toggle("is-open", isOpen);
    supportChatModal.setAttribute("aria-hidden", String(!isOpen));
    document.body.classList.toggle("support-chat-open", isOpen);
  };

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

  supportImageOpenButtons.forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      setSupportImageOpen(true, button.dataset.imageSrc || "", button.dataset.imageTitle || "");
    });
  });

  supportImageCloseButtons.forEach((button) => {
    button.addEventListener("click", () => setSupportImageOpen(false));
  });

  supportImageLightbox?.addEventListener("click", (event) => {
    if (event.target === supportImageLightbox) {
      setSupportImageOpen(false);
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
      setSupportImageOpen(false);
      setSupportChatOpen(false);
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
  setSupportImageOpen(false);
  setSupportChatOpen(supportChatModal?.classList.contains("is-open") || false);

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
