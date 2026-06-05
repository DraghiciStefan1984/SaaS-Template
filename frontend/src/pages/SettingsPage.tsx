import { BellRing, CalendarClock, Settings, SlidersHorizontal } from "lucide-react";
import { useState } from "react";

import { PageHeader } from "../components/PageHeader";
import { StatusBadge } from "../components/StatusBadge";

export function SettingsPage() {
  const [frequency, setFrequency] = useState("weekly");
  const [timezone, setTimezone] = useState("UTC");
  const [summaryStyle, setSummaryStyle] = useState("concise");

  return (
    <>
      <PageHeader eyebrow="Settings" icon={Settings} title="Product Settings" />

      <section className="settings-grid">
        <div className="tool-panel">
          <div className="panel-heading">
            <h2>Workflow</h2>
            <SlidersHorizontal aria-hidden="true" size={18} />
          </div>
          <form className="form-grid">
            <label>
              Default workflow
              <select defaultValue="one_click">
                <option value="one_click">One-click report</option>
                <option value="no_click">No-click monitor</option>
              </select>
            </label>
            <label>
              Summary style
              <select onChange={(event) => setSummaryStyle(event.target.value)} value={summaryStyle}>
                <option value="concise">Concise</option>
                <option value="detailed">Detailed</option>
                <option value="executive">Executive</option>
              </select>
            </label>
            <label className="toggle-control setting-toggle">
              <input defaultChecked type="checkbox" />
              Include AI conclusion
            </label>
          </form>
        </div>

        <div className="tool-panel">
          <div className="panel-heading">
            <h2>Schedule</h2>
            <CalendarClock aria-hidden="true" size={18} />
          </div>
          <form className="form-grid">
            <label>
              Frequency
              <select onChange={(event) => setFrequency(event.target.value)} value={frequency}>
                <option value="manual">Manual only</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
              </select>
            </label>
            <label>
              Timezone
              <select onChange={(event) => setTimezone(event.target.value)} value={timezone}>
                <option value="UTC">UTC</option>
                <option value="Europe/Bucharest">Europe/Bucharest</option>
                <option value="America/New_York">America/New_York</option>
              </select>
            </label>
            <StatusBadge value={frequency === "manual" ? "manual" : "scheduled"} />
          </form>
        </div>

        <div className="tool-panel">
          <div className="panel-heading">
            <h2>Delivery</h2>
            <BellRing aria-hidden="true" size={18} />
          </div>
          <form className="form-grid">
            <label className="toggle-control setting-toggle">
              <input defaultChecked type="checkbox" />
              Email reports
            </label>
            <label className="toggle-control setting-toggle">
              <input defaultChecked type="checkbox" />
              In-app alerts
            </label>
            <button className="secondary-button" disabled type="button">
              Save settings
            </button>
          </form>
        </div>
      </section>
    </>
  );
}
