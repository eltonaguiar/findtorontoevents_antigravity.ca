import { z } from "zod";

const emailSchema = z.string().trim().email().max(320);
const loginIdentifierSchema = z.string().trim().min(1).max(320);
const passwordSchema = z
  .string()
  .min(12)
  .max(128)
  .regex(/[A-Z]/, "Must include an uppercase letter")
  .regex(/[a-z]/, "Must include a lowercase letter")
  .regex(/\d/, "Must include a digit")
  .regex(/[^A-Za-z0-9]/, "Must include a symbol");

export const registerSchema = z.object({
  email: emailSchema,
  password: passwordSchema,
  displayName: z.string().trim().min(2).max(120),
});

export const loginSchema = z.object({
  email: loginIdentifierSchema,
  password: z.string().min(1).max(128),
});
