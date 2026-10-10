import { useEffect, useState } from "react";
import { getStats, getWorkers, getTasks, createTask } from "./api";
import "./App.css";

function App() {
  const [stats, setStats] = useState({
    queued: 0,
    running: 0,
    success: 0,
    failed: 0,
  });

  const [workers, setWorkers] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [wsStatus, setWsStatus] = useState("Connecting");
  const [taskType, setTaskType] = useState("fibonacci");
  const [payloadValue, setPayloadValue] = useState("20");
  const [submitting, setSubmitting] = useState(false);
  const [submitMessage, setSubmitMessage] = useState(null);

  const loadData = async () => {
    try {
      const [statsRes, workersRes, tasksRes] = await Promise.all([
        getStats(),
        getWorkers(),
        getTasks(),
      ]);

      setStats(statsRes.data);
      setWorkers(workersRes.data);
      setTasks(tasksRes.data);
    } catch (error) {
      console.error("Failed to load dashboard data:", error);
    }
  };

  const handleSubmitTask = async (e) => {
  e.preventDefault();
  setSubmitting(true);
  setSubmitMessage(null);

  const payload =
    taskType === "fibonacci"
      ? { n: Number(payloadValue) }
      : { seconds: Number(payloadValue) };

  try {
    const response = await createTask({
      task_type: taskType,
      payload,
    });

    setSubmitMessage({
      type: "success",
      text: `Task #${response.data.id} submitted successfully!`,
    });

    loadData();
  } catch (error) {
    setSubmitMessage({
      type: "error",
      text: error.response?.data?.detail || "Failed to submit task.",
    });
  } finally {
    setSubmitting(false);
  }
};

  useEffect(() => {
    let socket = null;
    let reconnectTimer = null;
    let isUnmounted = false;

    const connect = () => {
      setWsStatus("Connecting");

      socket = new WebSocket("ws://localhost:8000/ws");

      socket.onopen = () => {
        setWsStatus("Connected");
        loadData();
      };

      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);

        console.log("WebSocket event:", data);

        loadData();
      };

      socket.onerror = (error) => {
        console.error("WebSocket error:", error);
        setWsStatus("Disconnected");
      };

      socket.onclose = () => {
        setWsStatus("Reconnecting");

        if (!isUnmounted) {
          reconnectTimer = setTimeout(connect, 2000);
        }
      };
    };

    connect();

    return () => {
      isUnmounted = true;

      if (reconnectTimer) {
        clearTimeout(reconnectTimer);
      }

      if (socket) {
        if (socket.readyState === WebSocket.CONNECTING) {
          socket.addEventListener("open", () => socket.close());
        } else {
          socket.close();
        }
      }
    };
  }, []);

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div>
          <h1>TaskFlow</h1>
          <p>Distributed Task Processing System</p>
        </div>

        <div className="connection-status">
          <span
            className={`status-dot ${
              wsStatus === "Connected"
                ? "connected"
                : wsStatus === "Connecting"
                ? "connecting"
                : "disconnected"
            }`}
          />

          <span>WebSocket: {wsStatus}</span>
        </div>
      </header>

      <main>
        <section className="panel submit-panel">
  <div className="section-header">
    <h2>Submit Task</h2>
    <span>Enqueue a new job</span>
  </div>

  <form className="task-form" onSubmit={handleSubmitTask}>
    <label>
      Task Type
      <select
        value={taskType}
        onChange={(e) => {
          setTaskType(e.target.value);
          setPayloadValue(e.target.value === "fibonacci" ? "20" : "5");
          setSubmitMessage(null);
        }}
      >
        <option value="fibonacci">Fibonacci</option>
        <option value="sleep">Sleep</option>
      </select>
    </label>

    <label>
      {taskType === "fibonacci" ? "Number (n)" : "Duration (seconds)"}
      <input
        type="number"
        min="1"
        max={taskType === "fibonacci" ? "40" : "300"}
        value={payloadValue}
        onChange={(e) => setPayloadValue(e.target.value)}
        required
      />
    </label>

    <button type="submit" disabled={submitting}>
      {submitting ? "Submitting..." : "Submit Task"}
    </button>
  </form>

  {submitMessage && (
    <p className={`submit-message ${submitMessage.type}`}>
      {submitMessage.text}
    </p>
  )}
</section>
        {/* Stats */}
        <section>
          <h2>System Overview</h2>

          <div className="stats-grid">
            <div className="stat-card queued">
              <span>Queued</span>
              <strong>{stats.queued}</strong>
            </div>

            <div className="stat-card running">
              <span>Running</span>
              <strong>{stats.running}</strong>
            </div>

            <div className="stat-card success">
              <span>Success</span>
              <strong>{stats.success}</strong>
            </div>

            <div className="stat-card failed">
              <span>Failed</span>
              <strong>{stats.failed}</strong>
            </div>
          </div>
        </section>

        {/* Workers */}
        <section className="panel">
          <div className="section-header">
            <h2>Workers</h2>
            <span>{workers.length} registered</span>
          </div>

          {workers.length === 0 ? (
            <p className="empty">No workers registered.</p>
          ) : (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>Worker ID</th>
                    <th>Status</th>
                    <th>Last Heartbeat</th>
                  </tr>
                </thead>

                <tbody>
                  {workers.map((worker) => (
                    <tr key={worker.id}>
                      <td className="mono">{worker.worker_id}</td>

                      <td>
                        <span
                          className={`badge ${
                            worker.status === "ACTIVE"
                              ? "badge-active"
                              : "badge-dead"
                          }`}
                        >
                          {worker.status}
                        </span>
                      </td>

                      <td>
                        {worker.last_heartbeat
                          ? new Date(worker.last_heartbeat + "Z").toLocaleTimeString()
                          : "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>

        {/* Tasks */}
        <section className="panel">
          <div className="section-header">
            <h2>Tasks</h2>
            <span>{tasks.length} total</span>
          </div>

          {tasks.length === 0 ? (
            <p className="empty">No tasks submitted yet.</p>
          ) : (
            <div className="table-wrapper">
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Worker</th>
                    <th>Retries</th>
                    <th>Result</th>
                  </tr>
                </thead>

                <tbody>
                  {tasks.map((task) => (
                    <tr key={task.id}>
                      <td>#{task.id}</td>

                      <td>
                        <span className="task-type">{task.task_type}</span>
                      </td>

                      <td>
                        <span
                          className={`badge badge-${task.status.toLowerCase()}`}
                        >
                          {task.status}
                        </span>
                      </td>

                      <td className="mono">
                        {task.worker_id || "—"}
                      </td>

                      <td>{task.retry_count ?? 0}</td>

                      <td className="result">
                        {task.result || "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;