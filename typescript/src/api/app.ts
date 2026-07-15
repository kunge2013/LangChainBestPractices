// [AGC:START] tool=Cc author=fangkun
import { Hono } from "hono";
import { registerSandbox } from "./sandbox.js";

export const app = new Hono();

registerSandbox(app);
// [AGC:END]
