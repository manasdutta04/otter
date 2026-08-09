export function requireAuth(req: any, _res: any, next: () => void) {
  if (!req.headers.authorization) {
    throw new Error("unauthorized");
  }
  next();
}
