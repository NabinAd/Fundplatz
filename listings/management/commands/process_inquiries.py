"""Starte per `python manage.py process_inquiries --loop` in zweitem Terminal."""
import time
from django.core.management.base import BaseCommand, CommandError

from listings.draft_queue import next_queued_id, process_inquiry, recover_stale


class Command(BaseCommand):
    help = "Bearbeitet private Kundenanfragen-Entwuerfe ausserhalb von HTTP." 

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Genau einen Queue-Eintrag pruefen")
        parser.add_argument("--loop", action="store_true", help="Queue dauerhaft abarbeiten")
        parser.add_argument("--interval", type=float, default=2.0, help="Sekunden zwischen Pruefungen")
        parser.add_argument("--max-jobs", type=int, default=20, help="Maximale Jobs in einem Durchlauf")
        parser.add_argument("--recover-stale", action="store_true", help="Alte RUNNING-Jobs wieder einreihen")
        parser.add_argument("--stale-minutes", type=int, default=30)

    def handle(self, *args, **opts):
        if opts["once"] and opts["loop"]:
            raise CommandError("--once und --loop nicht kombinieren.")
        if not 0.5 <= opts["interval"] <= 3600:
            raise CommandError("--interval muss zwischen 0.5 und 3600 liegen.")
        if not 1 <= opts["max_jobs"] <= 10000:
            raise CommandError("--max-jobs muss zwischen 1 und 10000 liegen.")
        if opts["recover_stale"]:
            try:
                count = recover_stale(minutes=opts["stale_minutes"])
            except ValueError as exc:
                raise CommandError(str(exc)) from exc
            self.stdout.write(f"{count} haengengebliebene Anfragen zurueck in Queue.")
        processed = 0
        try:
            while True:
                job_id = next_queued_id()
                if job_id is None:
                    if not opts["loop"]:
                        break
                    time.sleep(opts["interval"])
                    continue
                if process_inquiry(job_id):
                    processed += 1
                    self.stdout.write(f"Anfrage #{job_id}: privater Entwurf bearbeitet.")
                if opts["once"] or (not opts["loop"] and processed >= opts["max_jobs"]):
                    break
        except KeyboardInterrupt:
            self.stdout.write("Worker beendet.")
        self.stdout.write(f"Fertig: {processed} Anfragen verarbeitet.")
