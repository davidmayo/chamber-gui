/**
 * experiment_cut_drag.js
 * Handles drag-and-drop reordering for experiment cut cards.
 */

(function () {
    "use strict";

    var dragSource = null;

    function clearDragOver() {
        document.querySelectorAll(".experiment-cut-card.drag-over").forEach(function (el) {
            el.classList.remove("drag-over");
        });
    }

    function pushCutOrderToDash(list) {
        if (!list) return;
        var order = Array.from(list.querySelectorAll(".experiment-cut-card"))
            .map(function (card) {
                var raw = card.getAttribute("data-cut-key");
                if (raw === null) return null;
                var parsed = parseInt(raw, 10);
                return Number.isFinite(parsed) ? parsed : null;
            })
            .filter(function (value) {
                return value !== null;
            });
        if (order.length === 0) return;
        window._pendingExperimentCutKeys = order;
        var syncButton = document.getElementById("experiment-cut-sync-btn");
        if (syncButton) syncButton.click();
    }

    function onDragStart(e) {
        dragSource = e.currentTarget;
        dragSource.classList.add("dragging");
        e.dataTransfer.effectAllowed = "move";
        // Firefox requires data to be set for drag/drop events.
        e.dataTransfer.setData("text/plain", dragSource.getAttribute("data-cut-key") || "");
    }

    function onDragOver(e) {
        e.preventDefault();
        e.dataTransfer.dropEffect = "move";
        var target = e.target.closest(".experiment-cut-card");
        if (!target || target === dragSource) return;
        clearDragOver();
        target.classList.add("drag-over");
    }

    function onDragLeave(e) {
        var target = e.target.closest(".experiment-cut-card");
        if (!target) return;
        target.classList.remove("drag-over");
    }

    function onDrop(e) {
        e.preventDefault();
        var list = e.currentTarget;
        var target = e.target.closest(".experiment-cut-card");
        clearDragOver();
        if (!list || !dragSource) return;

        if (!target) {
            list.appendChild(dragSource);
            pushCutOrderToDash(list);
            return;
        }
        if (target === dragSource) return;

        var allCards = Array.from(list.querySelectorAll(".experiment-cut-card"));
        var srcIndex = allCards.indexOf(dragSource);
        var targetIndex = allCards.indexOf(target);
        if (srcIndex < targetIndex) {
            list.insertBefore(dragSource, target.nextSibling);
        } else {
            list.insertBefore(dragSource, target);
        }
        pushCutOrderToDash(list);
    }

    function onDragEnd() {
        if (!dragSource) return;
        dragSource.classList.remove("dragging");
        dragSource.setAttribute("draggable", "false");
        dragSource = null;
        clearDragOver();
    }

    function attachCutCardListeners(list) {
        if (!list) return;
        list.querySelectorAll(".experiment-cut-card").forEach(function (card) {
            if (card.dataset.dragBindingsAttached === "1") return;
            card.dataset.dragBindingsAttached = "1";
            card.addEventListener("dragstart", onDragStart);
            card.addEventListener("dragend", onDragEnd);
        });
        list.querySelectorAll(".experiment-cut-drag-handle").forEach(function (handle) {
            if (handle.dataset.dragBindingsAttached === "1") return;
            handle.dataset.dragBindingsAttached = "1";
            var card = handle.closest(".experiment-cut-card");
            if (!card) return;
            handle.addEventListener("mousedown", function () {
                card.setAttribute("draggable", "true");
            });
            handle.addEventListener("mouseup", function () {
                if (dragSource !== card) {
                    card.setAttribute("draggable", "false");
                }
            });
            handle.addEventListener("mouseleave", function () {
                if (dragSource !== card) {
                    card.setAttribute("draggable", "false");
                }
            });
        });
    }

    function attachListListeners(list) {
        if (!list || list.dataset.dragContainerAttached === "1") return;
        list.dataset.dragContainerAttached = "1";
        list.addEventListener("dragover", onDragOver);
        list.addEventListener("dragleave", onDragLeave);
        list.addEventListener("drop", onDrop);
    }

    function bindExperimentCutDrag() {
        var modalBody = document.getElementById("experiment-modal-body");
        if (!modalBody) return;
        var list = modalBody.querySelector(".experiment-cut-list");
        if (!list) return;
        attachListListeners(list);
        attachCutCardListeners(list);
    }

    function initObserver() {
        var modalBody = document.getElementById("experiment-modal-body");
        if (!modalBody) {
            setTimeout(initObserver, 200);
            return;
        }
        bindExperimentCutDrag();
        var observer = new MutationObserver(function () {
            bindExperimentCutDrag();
        });
        observer.observe(modalBody, { childList: true, subtree: true });
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", initObserver);
    } else {
        initObserver();
    }
})();
