/**
 * Logistics Management System - Interactive Logic & Live Transit Timer
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Live Transit Duration Counter for In-Transit Shipments
    const timerElement = document.getElementById('live-transit-timer');
    if (timerElement) {
        const dispatchIso = timerElement.getAttribute('data-dispatch-time');
        if (dispatchIso) {
            const dispatchDate = new Date(dispatchIso).getTime();
            
            function updateLiveTimer() {
                const now = new Date().getTime();
                const diffMs = Math.max(0, now - dispatchDate);
                
                const totalSeconds = Math.floor(diffMs / 1000);
                const days = Math.floor(totalSeconds / 86400);
                const hours = Math.floor((totalSeconds % 86400) / 3600);
                const minutes = Math.floor((totalSeconds % 3600) / 60);
                const seconds = totalSeconds % 60;
                
                let timeStr = "";
                if (days > 0) timeStr += `${days}d `;
                timeStr += `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
                
                timerElement.textContent = timeStr;
            }
            
            updateLiveTimer();
            setInterval(updateLiveTimer, 1000);
        }
    }

    // 2. Mobile Sidebar Toggle
    const toggleBtn = document.getElementById('sidebar-toggle');
    const sidebar = document.querySelector('.sidebar');
    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener('click', () => {
            sidebar.classList.toggle('open');
        });
    }

    // 3. Auto-dismiss alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.4s ease';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 400);
        }, 5000);
    });
});
