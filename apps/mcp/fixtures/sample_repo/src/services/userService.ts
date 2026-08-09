import { insertUser } from "../repositories/userRepository.js";

export async function createUser(email: string) {
  return insertUser(email);
}
