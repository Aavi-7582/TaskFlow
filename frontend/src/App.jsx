import { useEffect, useState } from "react";
import { getStats, getWorkers, getTasks } from "./api";

function App() {
  const [stats, setStats] = useState({});
  const [workers, setWorkers] = useState([]);
  const [tasks, setTasks] = useState([]);

  const loadData = async () => {
    const [statsRes, workersRes, tasksRes] = await Promise.all([
      getStats(),
      getWorkers(),
      getTasks(),
    ]);

    setStats(statsRes.data);
    setWorkers(workersRes.data);
    setTasks(tasksRes.data);
  };


useEffect(() => {
  let socket = null;
  let reconnectTimer = null;
  let isUnmounted = false;

  const connect = () => {
    socket = new WebSocket("ws://localhost:8000/ws");

    socket.onopen = () => {
      // Load current data as soon as the socket connects, so the
      // dashboard is populated right away (also heals on reconnects)
      loadData();
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);

      console.log("WebSocket event:", data);

      loadData();
    };

    socket.onerror = (error) => {
      console.error("WebSocket error:", error);
    };

    socket.onclose = () => {
      // Auto-reconnect so the dashboard recovers when the backend
      // restarts or was not running yet (skipped when unmounting)
      if (!isUnmounted) {
        reconnectTimer = setTimeout(connect, 2000);
      }
    };
  };

  connect();

  return () => {
    isUnmounted = true;

    if (reconnectTimer) clearTimeout(reconnectTimer);

    if (socket) {
      // Close only after the handshake finishes, otherwise the browser
      // logs "WebSocket is closed before the connection is established"
      if (socket.readyState === WebSocket.CONNECTING) {
        socket.addEventListener("open", () => socket.close());
      } else {
        socket.close();
      }
    }
  };
}, []);

  return (
    <div>
      <h1>TaskFlow Dashboard</h1>

      <h2>Stats</h2>
      <p>Queued: {stats.queued}</p>
      <p>Running: {stats.running}</p>
      <p>Success: {stats.success}</p>
      <p>Failed: {stats.failed}</p>

      <h2>Workers</h2>
      {workers.map((worker) => (
        <p key={worker.id}>
          {worker.worker_id} — {worker.status}
        </p>
      ))}

      <h2>Tasks</h2>
      {tasks.map((task) => (
        <p key={task.id}>
          #{task.id} — {task.task_type} — {task.status}
        </p>
      ))}
    </div>
  );
}

export default App;