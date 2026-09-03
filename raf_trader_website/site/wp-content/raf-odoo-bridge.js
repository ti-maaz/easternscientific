(function () {
    "use strict";

    function showMessage(form, message, isSuccess) {
        var existing = form.parentElement.querySelector(".raf-odoo-form-message");
        if (existing) {
            existing.remove();
        }

        var feedback = document.createElement("div");
        feedback.className = "raf-odoo-form-message elementor-message " +
            (isSuccess ? "elementor-message-success" : "elementor-message-danger");
        feedback.setAttribute("role", "alert");
        feedback.style.marginTop = "12px";
        feedback.style.color = isSuccess ? "#198754" : "#b02a37";
        feedback.textContent = message;
        form.insertAdjacentElement("afterend", feedback);
    }

    document.addEventListener("submit", function (event) {
        var form = event.target.closest("form.elementor-form");
        if (!form) {
            return;
        }

        event.preventDefault();
        event.stopImmediatePropagation();

        var submitButton = form.querySelector('button[type="submit"]');
        var formData = new FormData(form);
        formData.set("source_url", window.location.pathname);

        if (submitButton) {
            submitButton.disabled = true;
        }

        fetch("/raf-trader/inquiry", {
            method: "POST",
            body: formData,
            credentials: "same-origin",
            headers: {"X-Requested-With": "XMLHttpRequest"},
        })
            .then(function (response) {
                return response.json().then(function (data) {
                    if (!response.ok || !data.ok) {
                        throw new Error(data.message || "Unable to submit the form.");
                    }
                    return data;
                });
            })
            .then(function (data) {
                form.reset();
                showMessage(form, data.message, true);
            })
            .catch(function (error) {
                showMessage(form, error.message || "Unable to submit the form.", false);
            })
            .finally(function () {
                if (submitButton) {
                    submitButton.disabled = false;
                }
            });
    }, true);
})();
