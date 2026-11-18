const runButton = document.getElementById("run-button");
const statusText = document.getElementById("status");

runButton.addEventListener("click", function () {
    const start = document.getElementById("start").value;
    const goal = document.getElementById("goal").value;

    statusText.textContent = `Selected: ${start} to ${goal}. Search connection comes next.`;
});