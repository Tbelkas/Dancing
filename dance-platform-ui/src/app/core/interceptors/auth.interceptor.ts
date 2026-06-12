import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const token = auth.getToken();

  const authReq = token
    ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
    : req;

  return next(authReq).pipe(
    catchError(err => {
      // Only treat 401 as an expired/invalid session when the request was
      // actually authenticated — a failed login is not a session loss.
      if (err.status === 401 && token) {
        auth.logout();
      }
      return throwError(() => err);
    })
  );
};
