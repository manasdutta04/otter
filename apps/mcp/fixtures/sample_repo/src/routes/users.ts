import express from "express";
import { createUser } from "../services/userService.js";

export function registerUserRoutes(app: express.Express) {
  app.post("/users", async (req, res) => {
    const user = await createUser(req.body.email);
    res.json(user);
  });
}
