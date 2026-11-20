const runButton = document.getElementById("run-button");
const statusText = document.getElementById("status");
const resultsBody = document.getElementById("results-body");

runButton.addEventListener("click", async function () {
    const start = document.getElementById("start").value;
    const goal = document.getElementById("goal").value;

    runButton.disabled = true;
    resultsBody.innerHTML = "";
    statusText.textContent = "Running both searches...";

    try {
        const response = await fetch("/api/run", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                kind: "road",
                start: start,
                goal: goal,
                scenario: "none"
            })
        });

        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Search failed.");
        }

        if (!result.flat.found || !result.tier.found) {
            statusText.textContent = "No route found.";
            return;
        }

        resultsBody.innerHTML = `
    <tr>
        <td>Distance (m)</td>
        <td>${result.flat.cost.toFixed(1)}</td>
        <td>${result.tier.cost.toFixed(1)}</td>
    </tr>
    <tr>
        <td>Detailed node expansions</td>
        <td>${result.flat.nodes}</td>
        <td>${result.tier.nodes}</td>
    </tr>
    <tr>
        <td>Abstract node expansions</td>
        <td>${result.flat.abstract_nodes}</td>
        <td>${result.tier.abstract_nodes}</td>
    </tr>
    <tr>
        <td>Query time (ms)</td>
        <td>${result.flat.runtime_ms.toFixed(2)}</td>
        <td>${result.tier.runtime_ms.toFixed(2)}</td>
    </tr>
    <tr>
        <td>Region preparation time (ms)</td>
        <td>—</td>
        <td>${result.tier.preprocess_ms.toFixed(2)}</td>
    </tr>
`;

statusText.textContent = "Comparison complete.";

    } catch (error) {
        statusText.textContent = `Error: ${error.message}`;
    } finally {
        runButton.disabled = false;
    }
});