```javascript
document.addEventListener('DOMContentLoaded', () => {

    // ========================================================
    // 1. Variables
    // ========================================================

    let scoreChart, statusChart;

    const analyzeBtn = document.getElementById('analyze-btn');
    const resultsSection = document.getElementById('results-section');
    const resultsBody = document.getElementById('results-body');
    const jdArea = document.getElementById('job-description');
    const fileInput = document.getElementById('file-input');
    const fileList = document.getElementById('file-list');


    // ========================================================
    // 2. Analyze Button
    // ========================================================

    analyzeBtn.addEventListener('click', async () => {

        const jd = jdArea.value.trim();
        const files = fileInput.files;

        if (!jd || files.length === 0) {
            alert("Please provide both Job Description and at least one Resume!");
            return;
        }

        analyzeBtn.disabled = true;
        analyzeBtn.innerHTML =
            '<i class="fas fa-spinner fa-spin"></i> Processing...';

        const formData = new FormData();

        formData.append('jd', jd);

        Array.from(files).forEach(file => {
            formData.append('resumes', file);
        });


        try {

            const response = await fetch(
                'http://127.0.0.1:8080/analyze',
                {
                    method: 'POST',
                    body: formData
                }
            );

            if (!response.ok) {
                throw new Error("Backend server error");
            }

            const data = await response.json();

            console.log("Backend response:", data);

            displayResults(data);

        } catch (error) {

            console.error("Error connecting to backend:", error);

            alert(
                "Could not connect to the Python server. " +
                "Make sure app.py is running on port 8080!"
            );

        } finally {

            analyzeBtn.disabled = false;

            analyzeBtn.innerHTML =
                '<i class="fas fa-bolt"></i> Analyze Resumes';
        }

    });


    // ========================================================
    // 3. Display Results
    // ========================================================

    function displayResults(results) {

        resultsBody.innerHTML = "";

        resultsSection.style.display = "block";


        if (results.length === 0) {

            resultsBody.innerHTML =
                "<tr><td colspan='4' style='text-align:center;'>" +
                "No results found." +
                "</td></tr>";

            return;
        }


        results.forEach((res, index) => {

            const rowId = `candidate-row-${index}`;


            // ------------------------------------------------
            // Main candidate row
            // ------------------------------------------------

            const mainRow = document.createElement('tr');

            mainRow.className = 'candidate-row';


            const badge = index === 0
                ? '<span class="top-match-badge">' +
                  '<i class="fas fa-crown"></i> Top Match' +
                  '</span>'
                : '';


            mainRow.innerHTML = `

                <td>
                    <strong>${escapeHtml(res.name)}</strong>
                    ${badge}
                </td>

                <td>
                    <span class="score-pill ${scoreClass(res.score)}">
                        ${res.score}%
                    </span>
                </td>

                <td>
                    <span class="status-badge">
                        ${escapeHtml(res.status)}
                    </span>
                </td>

                <td>

                    <button
                        class="details-btn"
                        data-target="${rowId}"
                    >

                        <span>Skills</span>

                        <i class="fas fa-chevron-down"></i>

                    </button>

                </td>
            `;


            // ------------------------------------------------
            // Hidden row containing matched + missing skills
            // ------------------------------------------------

            const detailRow = document.createElement('tr');

            detailRow.className = 'details-row';

            detailRow.id = rowId;


            detailRow.innerHTML = `

                <td colspan="4">

                    <div class="accordion-content">

                        <div class="accordion-inner">

                            <!-- MATCHED SKILLS -->

                            <div class="skills-block">

                                <h4>
                                    <i class="fas fa-check-circle"></i>
                                    Matched Skills
                                </h4>

                                <div class="skills-container">

                                    ${renderSkillTagsHtml(
                                        res.matched_skills,
                                        'matched'
                                    )}

                                </div>

                            </div>


                            <!-- MISSING SKILLS -->

                            <div class="skills-block missing">

                                <h4>
                                    <i class="fas fa-exclamation-circle"></i>
                                    Missing Skills
                                </h4>

                                <div class="skills-container">

                                    ${renderSkillTagsHtml(
                                        res.missing_skills,
                                        'missing'
                                    )}

                                </div>

                            </div>

                        </div>

                    </div>

                </td>
            `;


            resultsBody.appendChild(mainRow);

            resultsBody.appendChild(detailRow);

        });


        // ====================================================
        // Attach Skills button events
        // ====================================================

        resultsBody
            .querySelectorAll('.details-btn')
            .forEach(button => {

                button.addEventListener(
                    'click',
                    () => toggleAccordion(button)
                );

            });


        renderCharts(results);

        resultsSection.scrollIntoView({
            behavior: 'smooth'
        });

    }


    // ========================================================
    // 4. Score Styling
    // ========================================================

    function scoreClass(score) {

        if (score >= 75) {
            return 'high-score';
        }

        if (score >= 50) {
            return 'med-score';
        }

        return '';
    }


    // ========================================================
    // 5. Render Skill Tags
    // ========================================================

    function renderSkillTagsHtml(skills, type) {

        if (!skills || skills.length === 0) {

            return '<span class="no-skills">None</span>';

        }


        return skills
            .map(skill => {

                const missingClass =
                    type === 'missing'
                        ? 'skill-tag-missing'
                        : '';

                return `
                    <span class="skill-tag ${missingClass}">
                        ${escapeHtml(skill)}
                    </span>
                `;

            })
            .join('');

    }


    // ========================================================
    // 6. Escape HTML
    // ========================================================

    function escapeHtml(str) {

        const div = document.createElement('div');

        div.textContent = str;

        return div.innerHTML;
    }


    // ========================================================
    // 7. Accordion Toggle
    // ========================================================

    function toggleAccordion(button) {

        const targetId = button.dataset.target;

        const targetRow =
            document.getElementById(targetId);

        if (!targetRow) {
            return;
        }


        const content =
            targetRow.querySelector('.accordion-content');

        const icon =
            button.querySelector('i');


        const isOpen =
            targetRow.classList.contains('open');


        if (isOpen) {

            content.style.maxHeight = '0px';

            targetRow.classList.remove('open');

            if (icon) {
                icon.style.transform = 'rotate(0deg)';
            }

        } else {

            content.style.maxHeight =
                content.scrollHeight + 'px';

            targetRow.classList.add('open');

            if (icon) {
                icon.style.transform = 'rotate(180deg)';
            }

        }

    }


    // ========================================================
    // 8. Charts
    // ========================================================

    function renderCharts(results) {

        const names =
            results.map(r => r.name.split(".")[0]);

        const scores =
            results.map(r => r.score);

        const strong =
            results.filter(
                r => r.status === "Strong Match"
            ).length;

        const review =
            results.length - strong;


        if (scoreChart) {
            scoreChart.destroy();
        }

        if (statusChart) {
            statusChart.destroy();
        }


        // ----------------------------------------------------
        // Score Chart
        // ----------------------------------------------------

        const scoreCanvas =
            document.getElementById("scoreChart");

        if (scoreCanvas) {

            const ctx1 =
                scoreCanvas.getContext("2d");

            scoreChart = new Chart(ctx1, {

                type: "bar",

                data: {

                    labels: names,

                    datasets: [{

                        label: "Match Score (%)",

                        data: scores,

                        backgroundColor: '#43b5ee'

                    }]
                },

                options: {
                    responsive: true
                }

            });

        }


        // ----------------------------------------------------
        // Status Chart
        // ----------------------------------------------------

        const statusCanvas =
            document.getElementById("statusChart");

        if (statusCanvas) {

            const ctx2 =
                statusCanvas.getContext("2d");

            statusChart = new Chart(ctx2, {

                type: "pie",

                data: {

                    labels: [
                        "Strong Match",
                        "Review"
                    ],

                    datasets: [{

                        data: [
                            strong,
                            review
                        ],

                        backgroundColor: [
                            '#22c55e',
                            '#f59e0b'
                        ]

                    }]
                },

                options: {
                    responsive: true
                }

            });

        }

    }


    // ========================================================
    // 9. File Selection
    // ========================================================

    fileInput.addEventListener('change', (e) => {

        handleFiles(e.target.files);

    });


    function handleFiles(files) {

        fileList.innerHTML = "";

        if (files.length === 0) {
            return;
        }


        Array.from(files).forEach(file => {

            const li =
                document.createElement('li');


            li.innerHTML = `

                <span style="
                    color: var(--text-main);
                    font-weight: 500;
                ">

                    <i class="fas fa-file-alt"></i>
                    ${escapeHtml(file.name)}

                </span>

                <i
                    class="fas fa-check-circle"
                    style="color: green;"
                ></i>

            `;


            fileList.appendChild(li);

        });

    }

});
```