import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { AuthService } from '../services/auth.service';
import { environment } from '../../../environments/environment';

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const auth = inject(AuthService);
  const token = auth.getToken();

  // Only ever attach the bearer token to our own API. Without this guard, any future request to a
  // third party (YouTube oEmbed, a thumbnail, analytics) would leak the user's session token.
  const isApiRequest = req.url.startsWith(environment.apiUrl);
  const authReq = token && isApiRequest
    ? req.clone({ setHeaders: { Authorization: `Bearer ${token}` } })
    : req;

  return next(authReq).pipe(
    catchError(err => {
      // Only treat 401 as an expired/invalid session when an authenticated request to our own
      // API failed — a failed login, or a third party's 401, is not a session loss.
      if (err.status === 401 && token && isApiRequest) {
        auth.logout();
      }
      return throwError(() => err);
    })
  );
};
