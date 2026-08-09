import { createUser } from "../src/services/userService.js";

export async function testCreateUser() {
  const user = await createUser("a@b.com");
  if (!user.email) throw new Error("missing email");
}
