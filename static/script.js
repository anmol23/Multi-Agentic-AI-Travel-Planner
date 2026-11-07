let currentThreadId = localStorage.getItem("travel_thread_id") || null;
let latestAnswerMarkdown = "";
let approvalPending = false;

function setPrompt(text) {
    document.getElementById("userInput").value = text;
}

function setLoading(isLoading) {
    const sendBtn = document.getElementById("sendBtn");
    const btnText = document.getElementById("btnText");
    const btnLoader = document.getElementById("btnLoader");

    sendBtn.disabled = isLoading || approvalPending;

    if (isLoading) {
        btnText.classList.add("hidden");
        btnLoader.classList.remove("hidden");
    } else {
        btnText.classList.remove("hidden");
        btnLoader.classList.add("hidden");
    }
}

function setApprovalLoading(isLoading) {
    document.getElementById("approveBtn").disabled = isLoading;
    document.getElementById("reviseBtn").disabled = isLoading;
}

function showError(message) {
    const errorBox = document.getElementById("errorBox");
    errorBox.textContent = message;
    errorBox.classList.remove("hidden");
}

function hideError() {
    const errorBox = document.getElementById("errorBox");
    errorBox.classList.add("hidden");
    errorBox.textContent = "";
}

function renderMarkdown(element, markdown) {
    const content = markdown || "";

    if (typeof marked !== "undefined") {
        element.innerHTML = marked.parse(content);
    } else {
        element.innerText = content;
    }
}

function showResult(answer, threadId) {
    latestAnswerMarkdown = answer || "";

    const resultSection = document.getElementById("resultSection");
    const resultBox = document.getElementById("resultBox");
    const threadInfo = document.getElementById("threadInfo");

    renderMarkdown(resultBox, latestAnswerMarkdown);
    threadInfo.textContent = `Thread ID: ${threadId || "-"}`;
    resultSection.classList.remove("hidden");

    resultSection.scrollIntoView({
        behavior: "smooth",
        block: "start"
    });
}

function showApproval(data) {
    const approvalSection = document.getElementById("approvalSection");
    const approvalRequest = document.getElementById("approvalRequest");

    approvalRequest.textContent =
        data.approval_request ||
        "Review the draft itinerary. Approve it or provide feedback for revision.";

    // Keep the draft visible in the result panel while asking for approval.
    const draft = data.itinerary || data.answer || "";

    if (draft) {
        showResult(draft, data.thread_id);
    }

    approvalPending = true;
    document.getElementById("sendBtn").disabled = true;
    approvalSection.classList.remove("hidden");

    approvalSection.scrollIntoView({
        behavior: "smooth",
        block: "center"
    });
}

function hideApproval() {
    document.getElementById("approvalSection").classList.add("hidden");
    document.getElementById("approvalFeedback").value = "";
    approvalPending = false;
    document.getElementById("sendBtn").disabled = false;
}

async function readApiResponse(response) {
    let data;

    try {
        data = await response.json();
    } catch {
        throw new Error(
            `Server returned an unreadable response (HTTP ${response.status}).`
        );
    }

    if (!response.ok || data.success === false) {
        throw new Error(
            data.error || `Request failed (HTTP ${response.status}).`
        );
    }

    return data;
}

async function sendMessage() {
    hideError();

    if (approvalPending) {
        showError(
            "Please approve the current draft or submit revision feedback before starting another trip."
        );
        return;
    }

    const input = document.getElementById("userInput");
    const message = input.value.trim();

    if (!message) {
        showError("Please enter your travel request first.");
        return;
    }

    setLoading(true);

    try {
        const response = await fetch("/api/travel", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                message: message,
                thread_id: currentThreadId
            })
        });

        const data = await readApiResponse(response);

        currentThreadId = data.thread_id;
        localStorage.setItem("travel_thread_id", currentThreadId);

        showResult(data.answer || data.itinerary || "", data.thread_id);

        if (data.requires_approval) {
            showApproval(data);
        } else {
            hideApproval();
        }

    } catch (error) {
        showError(error.message);

    } finally {
        setLoading(false);
    }
}

async function submitApproval(approved) {
    hideError();

    if (!currentThreadId) {
        showError(
            "The travel-plan thread could not be found. Please submit your travel request again."
        );
        return;
    }

    const feedback = document
        .getElementById("approvalFeedback")
        .value.trim();

    if (!approved && !feedback) {
        showError("Please enter feedback describing what you want changed.");
        document.getElementById("approvalFeedback").focus();
        return;
    }

    setApprovalLoading(true);

    try {
        const response = await fetch("/api/travel/approve", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                thread_id: currentThreadId,
                approved: approved,
                feedback: feedback
            })
        });

        const data = await readApiResponse(response);

        currentThreadId = data.thread_id || currentThreadId;
        localStorage.setItem("travel_thread_id", currentThreadId);

        showResult(data.answer || data.itinerary || "", currentThreadId);

        // A revision workflow may pause again to request approval
        // of the revised draft.
        if (data.requires_approval) {
            showApproval(data);
        } else {
            hideApproval();
        }

    } catch (error) {
        showError(error.message);

    } finally {
        setApprovalLoading(false);
    }
}

function copyResult() {
    const resultBox = document.getElementById("resultBox");
    const text = resultBox.innerText;

    if (!text) {
        return;
    }

    navigator.clipboard.writeText(text)
        .then(() => {
            const copyBtn = document.querySelector(".copy-btn");
            const oldText = copyBtn.textContent;

            copyBtn.textContent = "Copied!";

            setTimeout(() => {
                copyBtn.textContent = oldText;
            }, 1400);
        })
        .catch(() => {
            showError("Could not copy result.");
        });
}

function downloadPDF() {
    const pdfContent = document.getElementById("pdfContent");

    if (!latestAnswerMarkdown || !pdfContent) {
        showError("No travel plan available to download.");
        return;
    }

    const downloadBtn = document.querySelector(".download-btn");
    const oldText = downloadBtn.textContent;

    downloadBtn.textContent = "Preparing PDF...";
    downloadBtn.disabled = true;

    const options = {
        margin: 0.5,
        filename: "ai-travel-plan.pdf",
        image: {
            type: "jpeg",
            quality: 0.98
        },
        html2canvas: {
            scale: 2,
            useCORS: true,
            backgroundColor: "#ffffff"
        },
        jsPDF: {
            unit: "in",
            format: "a4",
            orientation: "portrait"
        },
        pagebreak: {
            mode: ["avoid-all", "css", "legacy"]
        }
    };

    html2pdf()
        .set(options)
        .from(pdfContent)
        .save()
        .then(() => {
            downloadBtn.textContent = oldText;
            downloadBtn.disabled = false;
        })
        .catch(() => {
            downloadBtn.textContent = oldText;
            downloadBtn.disabled = false;
            showError("Could not download PDF.");
        });
}

document.addEventListener("keydown", function (event) {
    if (event.ctrlKey && event.key === "Enter") {
        sendMessage();
    }
});