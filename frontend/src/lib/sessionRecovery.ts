import { ApiError } from "@/lib/api-client";

/**
 * Is this failure a reason to destroy the stored session token?
 *
 * Only one answer is yes. `App` bootstraps by calling `/auth/me`, and it used
 * to clear the token on **any** rejection -- so a backend that was restarting,
 * a request that timed out, or a laptop that had just woken up signed the user
 * out. Reproduced on 2026-09-09 by restarting the API under an open tab: the
 * token was gone from `localStorage` afterwards and the password had to be
 * typed again.
 *
 * A 500 or an unreachable server says nothing about whether the session is
 * still valid; only a 401 does. Keeping the token through an outage costs
 * nothing -- the user still lands on the sign-in page for that render, because
 * there is no user object to show an app with -- and the next load once the
 * server answers signs them straight back in.
 *
 * The same shape as the "remember me" defect this project already records: the
 * failure of something transient sat inside the path of something that is not.
 */
export function shouldForgetSession(error: unknown): boolean {
  return error instanceof ApiError && error.status === 401;
}
