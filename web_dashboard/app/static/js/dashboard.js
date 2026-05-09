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
    const table = referralTree.closest("table");
    const columnCount = table?.querySelectorAll("thead th").length || 14;

    const makeCell = (text = "") => {
      const cell = document.createElement("td");
      cell.textContent = text;
      return cell;
    };

    const makeStatusCell = (text = "") => {
      const cell = document.createElement("td");
      const status = document.createElement("span");
      status.className = "status admin-status-pill";
      status.textContent = text || "-";
      cell.append(status);
      return cell;
    };

    const makeDetailLink = (user, label = "Open Account") => {
      const link = document.createElement("a");
      link.className = "admin-user-link referral-account-link";
      link.href = user.detail_url || `/users/${user.id}`;
      link.textContent = label;
      return link;
    };

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
      const form = makePostActionForm(user.delete_url || `/users/${user.id}/delete`, "danger-button", "Delete");
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

    const removeDescendantRows = (userId) => {
      const id = String(userId);
      Array.from(referralTree.querySelectorAll("[data-ancestor-ids]")).forEach((row) => {
        const ancestors = (row.dataset.ancestorIds || "").split(",").filter(Boolean);
        if (!ancestors.includes(id)) {
          return;
        }
        if (row.dataset.userId) {
          expandedNodes.delete(row.dataset.userId);
        }
        row.remove();
      });
      expandedNodes.delete(id);
    };

    const makeFeedbackRow = (parentRow, message, type = "loading") => {
      const row = document.createElement("tr");
      row.className = `referral-child-row referral-${type}-row`;
      row.dataset.ancestorIds = [
        ...(parentRow.dataset.ancestorIds || "").split(",").filter(Boolean),
        parentRow.dataset.userId,
      ].join(",");

      const cell = document.createElement("td");
      cell.colSpan = columnCount;
      cell.textContent = message;
      row.append(cell);
      return row;
    };

    const makeTreeControls = (user, level) => {
      const node = document.createElement("div");
      node.className = "referral-tree-node is-child";
      node.style.setProperty("--tree-indent", `${level * 28}px`);

      if (user.has_children) {
        const toggle = document.createElement("button");
        toggle.className = "referral-tree-toggle";
        toggle.type = "button";
        toggle.dataset.referralToggle = "";
        toggle.dataset.userId = String(user.id);
        toggle.dataset.treeLevel = String(level);
        toggle.dataset.childrenCount = String(user.children_count || user.referrals_count || 0);
        toggle.setAttribute("aria-expanded", "false");
        toggle.textContent = "View";
        node.append(toggle);

        const count = document.createElement("span");
        count.className = "referral-tree-count";
        count.textContent = `Referrals: ${user.children_count || user.referrals_count || 0}`;
        node.append(count);
      } else {
        const spacer = document.createElement("span");
        spacer.className = "referral-tree-spacer";
        spacer.setAttribute("aria-hidden", "true");
        node.append(spacer);

        const empty = document.createElement("span");
        empty.className = "referral-tree-count is-empty";
        empty.textContent = "No referrals";
        node.append(empty);
      }

      const name = document.createElement("span");
      name.className = "referral-tree-name";
      name.textContent = user.name || "-";
      node.append(name, makeDetailLink(user));
      return node;
    };

    const makeChildRow = (user, level, ancestorIds) => {
      const row = document.createElement("tr");
      row.className = "referral-child-row";
      row.dataset.userRow = "";
      row.dataset.userId = String(user.id);
      row.dataset.treeLevel = String(level);
      row.dataset.ancestorIds = ancestorIds.join(",");

      const nameCell = document.createElement("td");
      nameCell.append(makeTreeControls(user, level));
      row.append(nameCell);

      const usernameCell = document.createElement("td");
      usernameCell.append(makeDetailLink(user, user.username || "-"));
      row.append(usernameCell);

      row.append(
        makeCell(user.email || "-"),
        makeCell(`$${user.capital || "0.00"}`),
        makeCell(`$${user.profits || "0.0000"}`),
        makeStatusCell(user.plan || "none"),
        makeStatusCell(user.status || "active"),
        makeCell(user.referrer || "-"),
        makeCell(String(user.referrals_count || 0)),
        makeStatusCell(user.rank || "-"),
        makeCell(user.last_start_at || "-"),
        makeCell(user.created_at || "-"),
      );

      const passwordCell = document.createElement("td");
      const resetButton = document.createElement("button");
      resetButton.className = "safe-button";
      resetButton.type = "button";
      resetButton.textContent = "Reset password";
      passwordCell.append(resetButton);
      row.append(passwordCell);

      const actionsCell = document.createElement("td");
      const actions = document.createElement("div");
      actions.className = "admin-user-name-actions";
      actions.append(
        makePostActionForm(user.message_url || `/users/${user.id}/message`, "admin-message-button", "Send Message"),
        makeDetailLink(user, "Details"),
        makeDeleteForm(user),
      );
      actionsCell.append(actions);
      row.append(actionsCell);
      return row;
    };

    const renderChildren = (parentRow, parentId, children) => {
      removeDescendantRows(parentId);

      const parentAncestors = (parentRow.dataset.ancestorIds || "").split(",").filter(Boolean);
      const ancestorIds = [...parentAncestors, String(parentId)];
      const level = Number(parentRow.dataset.treeLevel || 0) + 1;
      const fragment = document.createDocumentFragment();

      if (!children.length) {
        fragment.append(makeFeedbackRow(parentRow, "No children found.", "empty"));
      } else {
        children.forEach((child) => {
          fragment.append(makeChildRow(child, level, ancestorIds));
        });
      }

      parentRow.after(fragment);
      expandedNodes.add(String(parentId));
      setToggleState(parentRow.querySelector(`[data-referral-toggle][data-user-id="${parentId}"]`), true);
    };

    referralTree.addEventListener("click", (event) => {
      const button = event.target.closest("[data-referral-toggle]");
      if (!button || !referralTree.contains(button)) {
        return;
      }

      const parentRow = button.closest("[data-user-row]");
      const userId = button.dataset.userId;

      if (!parentRow || !userId) {
        return;
      }

      if (expandedNodes.has(userId)) {
        removeDescendantRows(userId);
        setToggleState(button, false);
        return;
      }

      if (childrenCache.has(userId)) {
        renderChildren(parentRow, userId, childrenCache.get(userId));
        return;
      }

      removeDescendantRows(userId);
      const loadingRow = makeFeedbackRow(parentRow, "Loading children...", "loading");
      parentRow.after(loadingRow);
      setToggleLoading(button, true);

      fetch(`/users/${userId}/children`, {
        credentials: "same-origin",
        headers: { Accept: "application/json" },
      })
        .then((response) => {
          if (!response.ok) {
            throw new Error("Could not load children.");
          }
          return response.json();
        })
        .then((data) => {
          const children = Array.isArray(data.children) ? data.children : [];
          childrenCache.set(userId, children);
          loadingRow.remove();
          setToggleLoading(button, false);
          renderChildren(parentRow, userId, children);
        })
        .catch((error) => {
          loadingRow.remove();
          setToggleLoading(button, false);
          const errorRow = makeFeedbackRow(parentRow, error.message || "Could not load children.", "error");
          parentRow.after(errorRow);
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
