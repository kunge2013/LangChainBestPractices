import { Hono } from "hono";
import { registerCopilotKit } from "./copilotkit.js";
import { registerSandbox } from "./sandbox.js";

export const app = new Hono();

registerSandbox(app);
registerCopilotKit(app);
