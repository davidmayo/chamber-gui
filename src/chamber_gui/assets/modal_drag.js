/**
 * modal_drag.js
 * Handles drag-and-drop reordering and checkbox interaction inside the
 * "Select Graphs" modal.  Communicates config changes back to Dash via the
 * window._pendingConfig / #config-sync-btn bridge.
 */

(function () {
    "use strict";

    // -----------------------------------------------------------------------
    // Read current state from modal DOM
    // -----------------------------------------------------------------------
    function readModalConfig() {
        var items = document.querySelectorAll("#modal-body .modal-item");
        var config = [];
        items.forEach(function (el, index) {
            var panelId = el.getAttribute("data-panel-id");
            var cb = el.querySelector(".modal-checkbox");
            config.push({
                id: panelId,
                enabled: cb ? cb.classList.contains("modal-checkbox--on") : true,
                order: index,
            });
        });
        return config;
    }

    // -----------------------------------------------------------------------
    // Push config to Dash via the hidden button bridge
    // -----------------------------------------------------------------------
    function pushConfigToDash() {
        var config = readModalConfig();
        window._pendingConfig = config;
        var btn = document.getElementById("config-sync-btn");
        if (btn) {
            btn.click();
        }
    }

    // -----------------------------------------------------------------------
    // Drag-and-drop state
    // -----------------------------------------------------------------------
    var _dragSrc = null;

    function onDragStart(e) {
        _dragSrc = e.currentTarget;
        _dragSrc.classList.add("dragging");
        e.dataTransfer.effectAllowed = "move";
        // Required for Firefox
        e.dataTransfer.setData("text/plain", "");
    }

    function onDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = "move";
        var target = e.target.closest(".modal-item");
        if (!target || target === _dragSrc) return;
        clearDragOver();
        target.classList.add("drag-over");
    }

    function onDragLeave(e) {
        var target = e.target.closest(".modal-item");
        if (target) target.classList.remove("drag-over");
    }

    function onDrop(e) {
        e.preventDefault();
        var target = e.target.closest(".modal-item");
        clearDragOver();
        if (!target || !_dragSrc || target === _dragSrc) return;

        var list = target.parentNode;
        var allItems = Array.from(list.children);
        var srcIdx = allItems.indexOf(_dragSrc);
        var tgtIdx = allItems.indexOf(target);

        if (srcIdx < tgtIdx) {
            list.insertBefore(_dragSrc, target.nextSibling);
        } else {
            list.insertBefore(_dragSrc, target);
        }

        pushConfigToDash();
    }

    function onDragEnd() {
        if (_dragSrc) {
            _dragSrc.classList.remove("dragging");
            _dragSrc = null;
        }
        clearDragOver();
    }

    function clearDragOver() {
        document.querySelectorAll(".modal-item.drag-over").forEach(function (el) {
            el.classList.remove("drag-over");
        });
    }

    // -----------------------------------------------------------------------
    // Attach per-item listeners (called after each Dash render of modal-body)
    // -----------------------------------------------------------------------
    function attachItemListeners(modalBody) {
        modalBody.querySelectorAll(".drag-handle").forEach(function (handle) {
            var row = handle.closest(".modal-item");
            if (!row) return;
            // Enable dragging only when initiated via the handle
            handle.addEventListener("mousedown", function () {
                row.setAttribute("draggable", "true");
            });
            handle.addEventListener("mouseup", function () {
                row.setAttribute("draggable", "false");
            });
            row.addEventListener("dragstart", onDragStart);
            row.addEventListener("dragend", onDragEnd);
        });
    }

    // -----------------------------------------------------------------------
    // Sync all group checkboxes to reflect current individual checkbox states
    // -----------------------------------------------------------------------
    function syncGroupCheckboxes(modalBody) {
        modalBody.querySelectorAll(".group-item").forEach(function (groupItem) {
            var members = groupItem.getAttribute("data-members").split(",");
            var onCount = members.filter(function (m) {
                var cb = modalBody.querySelector(".modal-item[data-panel-id='" + m + "'] .modal-checkbox");
                return cb && cb.classList.contains("modal-checkbox--on");
            }).length;
            var groupCb = groupItem.querySelector(".modal-checkbox");
            if (!groupCb) return;
            if (onCount === members.length) {
                groupCb.className = "modal-checkbox modal-checkbox--on";
                groupCb.textContent = "\u2713";
            } else if (onCount === 0) {
                groupCb.className = "modal-checkbox";
                groupCb.textContent = "\u2713";
            } else {
                groupCb.className = "modal-checkbox modal-checkbox--mixed";
                groupCb.textContent = "\u2212";
            }
        });
    }

    // -----------------------------------------------------------------------
    // Delegated listeners on modal-body container (survive Dash re-renders)
    // -----------------------------------------------------------------------
    function attachContainerListeners(modalBody) {
        modalBody.addEventListener("dragover", onDragOver);
        modalBody.addEventListener("dragleave", onDragLeave);
        modalBody.addEventListener("drop", onDrop);
        modalBody.addEventListener("click", function (e) {
            // Group checkbox click
            var groupItem = e.target.closest(".group-item");
            if (groupItem) {
                var members = groupItem.getAttribute("data-members").split(",");
                // If all are on, turn all off; otherwise (mixed or all off) turn all on
                var allOn = members.every(function (m) {
                    var cb = modalBody.querySelector(".modal-item[data-panel-id='" + m + "'] .modal-checkbox");
                    return cb && cb.classList.contains("modal-checkbox--on");
                });
                members.forEach(function (m) {
                    var cb = modalBody.querySelector(".modal-item[data-panel-id='" + m + "'] .modal-checkbox");
                    if (cb) cb.classList.toggle("modal-checkbox--on", !allOn);
                });
                syncGroupCheckboxes(modalBody);
                pushConfigToDash();
                return;
            }
            // Individual checkbox toggle
            var cb = e.target.closest(".modal-item .modal-checkbox");
            if (cb) {
                cb.classList.toggle("modal-checkbox--on");
                syncGroupCheckboxes(modalBody);
                pushConfigToDash();
            }
        });
    }

    // -----------------------------------------------------------------------
    // Observe modal-body for content changes (Dash re-renders on each open)
    // -----------------------------------------------------------------------
    function initObserver() {
        var modalBody = document.getElementById("modal-body");
        if (!modalBody) {
            setTimeout(initObserver, 200);
            return;
        }

        attachContainerListeners(modalBody);

        var observer = new MutationObserver(function (mutations) {
            mutations.forEach(function (mutation) {
                if (mutation.type === "childList" && mutation.addedNodes.length > 0) {
                    attachItemListeners(modalBody);
                    syncGroupCheckboxes(modalBody);
                }
            });
        });

        observer.observe(modalBody, { childList: true, subtree: false });
    }

    // -----------------------------------------------------------------------
    // Bootstrap
    // -----------------------------------------------------------------------
    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initObserver);
    } else {
        initObserver();
    }
})();
