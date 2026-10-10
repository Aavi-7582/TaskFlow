import axios from "axios";

const API = axios.create({
  baseURL: "http://localhost:8000",
});

export const getStats = () => API.get("/stats");
export const getWorkers = () => API.get("/workers");
export const getTasks = () => API.get("/tasks");
export const createTask = (task) => API.post("/tasks", task);