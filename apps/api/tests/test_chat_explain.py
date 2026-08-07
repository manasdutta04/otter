from pathlib import Path

from packages.retrieval import answer_repository_question, clear_index_cache


def test_chat_explains_auth_not_only_file_pointer(tmp_path: Path):
    routes = tmp_path / "backend" / "src" / "routes"
    routes.mkdir(parents=True)
    (routes / "auth.route.js").write_text(
        "\n".join(
            [
                'import express from "express";',
                'import { protectRoute } from "../middlewares/auth.middleware.js";',
                'import { login, signup, logout, checkAuth } from "../controllers/auth.controller.js";',
                "const router = express.Router();",
                'router.post("/signup", signup);',
                'router.post("/login", login);',
                'router.post("/logout", logout);',
                'router.get("/check", protectRoute, checkAuth);',
                "export default router;",
            ]
        ),
        encoding="utf-8",
    )
    mw = tmp_path / "backend" / "src" / "middlewares"
    mw.mkdir(parents=True)
    (mw / "auth.middleware.js").write_text(
        "\n".join(
            [
                'import jwt from "jsonwebtoken";',
                "export const protectRoute = (req, res, next) => {",
                "  const token = req.cookies.jwt;",
                '  if (!token) return res.status(401).json({ message: "Unauthorized" });',
                "  const decoded = jwt.verify(token, process.env.JWT_SECRET);",
                "  req.user = decoded;",
                "  next();",
                "};",
            ]
        ),
        encoding="utf-8",
    )

    clear_index_cache()
    result = answer_repository_question(tmp_path, "how the auth managed?")
    answer = result["answer"].lower()
    assert "auth" in answer
    assert "best place to start" not in answer
    assert any(token in answer for token in ("jwt", "login", "protectroute", "signup", "router"))
    assert result.get("contexts")
