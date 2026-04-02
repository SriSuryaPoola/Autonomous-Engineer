// Onboarding Tour Engine for AI Autonomous Engineer
export class OnboardingTour {
    constructor() {
        this.currentStep = 0;
        this.steps = [
            {
                elementId: "new-project-btn",
                text: "✨ Start by creating your first Engineering Project here.",
                position: "right"
            },
            {
                elementId: "task-input",
                text: "💬 Assign a task to your AI Team. Be specific about features or tests!",
                position: "top"
            },
            {
                elementId: "dashboard-view",
                text: "📊 Watch the execution in real-time. Track DAGs, logs, and agent heartbeats.",
                position: "center"
            },
            {
                elementId: "reports-view",
                text: "📄 Once finished, download your detailed Engineering Reports here.",
                position: "center"
            }
        ];
        
        this.overlay = document.getElementById('tour-overlay');
        this.card = document.getElementById('tour-step-card');
        this.text = document.getElementById('tour-text');
        this.nextBtn = document.getElementById('next-tour-btn');
        this.skipBtn = document.getElementById('skip-tour');

        this.nextBtn.onclick = () => this.next();
        this.skipBtn.onclick = () => this.hide();
    }

    start() {
        if (localStorage.getItem('engineer_tour_finished')) return;
        this.currentStep = 0;
        this.showStep();
        this.overlay.classList.remove('hidden');
    }

    showStep() {
        const step = this.steps[this.currentStep];
        this.text.textContent = step.text;
        
        // Highlight logic (simplified)
        const el = document.getElementById(step.elementId);
        if (el) {
            el.scrollIntoView({ behavior: 'smooth' });
            el.classList.add('tour-highlight');
        }

        if (this.currentStep === this.steps.length - 1) {
            this.nextBtn.textContent = "Finish";
        }
    }

    next() {
        const prevStep = this.steps[this.currentStep];
        document.getElementById(prevStep.elementId)?.classList.remove('tour-highlight');

        if (this.currentStep < this.steps.length - 1) {
            this.currentStep++;
            this.showStep();
        } else {
            this.hide();
            localStorage.setItem('engineer_tour_finished', 'true');
        }
    }

    hide() {
        this.overlay.classList.add('hidden');
        this.steps.forEach(s => {
            document.getElementById(s.elementId)?.classList.remove('tour-highlight');
        });
        localStorage.setItem('engineer_tour_finished', 'true');
    }

    reset() {
        localStorage.removeItem('engineer_tour_finished');
        this.start();
    }
}
