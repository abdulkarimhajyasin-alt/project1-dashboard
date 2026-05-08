(() => {
  const body = document.body;
  const drawer = document.querySelector("[data-admin-drawer]");
  const overlay = document.querySelector("[data-drawer-overlay]");
  const openButtons = Array.from(document.querySelectorAll("[data-drawer-open]"));
  const closeButtons = Array.from(document.querySelectorAll("[data-drawer-close]"));
  const notificationRoots = Array.from(document.querySelectorAll("[data-notification-root]"));

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
    }
  });

  document.addEventListener("click", (event) => {
    if (!event.target.closest("[data-notification-root]")) {
      closeNotifications();
    }
  });

  setDrawerOpen(false);
  closeNotifications();

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
