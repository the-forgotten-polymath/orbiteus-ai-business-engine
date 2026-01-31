/** Shape of `POST /api/auth/login` JSON when password is valid but 2FA is pending. */
export type LoginResponseLike = {
  requires_totp?: boolean;
};

export function loginNeedsTotpStep(data: LoginResponseLike): boolean {
  return data.requires_totp === true;
}
