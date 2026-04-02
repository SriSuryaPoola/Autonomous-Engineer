"""
Real-time Observability Dashboard for Phase 3.

Provides an asyncio background loop that continually refreshes the console with:
  - Active agents
  - Task DAG queue status
  - Task progress/failures/retry counts
"""

import asyncio
import os
import sys
from typing import Optional

def clear_console():
    os.system('cls' if os.name == 'nt' else 'clear')

class Dashboard:
    def __init__(self, orchestrator):
        self.orchestrator = orchestrator
        self.running = False
        self._task: Optional[asyncio.Task] = None

    async def _render_loop(self):
        while self.running:
            clear_console()
            print("=" * 60)
            print("🚀 Autonomous Engineering Team — LIVE OBSERVABILITY DASHBOARD")
            print("=" * 60)
            
            # Print HiClaw System Status
            print("\n" + self.orchestrator.coordinator.summary())
            
            # Print Memory Size / Task metrics if accessible from manager
            manager = self.orchestrator.manager
            if manager:
                print("\n📊 TASK DAG STATUS:")
                tasks_in_memory = manager.memory.get_context(last_n=5)
                # Print recent events instead of deep queue analysis to keep it clean
                print(f"Total Completed / Failed tracked: {len(manager._task_results)}")
                
                print("\n🛡️ FAILURE METRICS & RETRIES:")
                errs = manager.memory.get_errors()
                print(f"Recorded Tool Failures: {len(errs)}")
            
            print("\n(Press Ctrl+C to terminate or wait for pipeline completion...)")
            print("=" * 60)
            await asyncio.sleep(1.0)
            
    def start(self):
        if not self.running:
            self.running = True
            self._task = asyncio.create_task(self._render_loop())
            
    def stop(self):
        self.running = False
        if self._task:
            self._task.cancel()
