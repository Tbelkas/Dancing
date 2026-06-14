import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  { path: '', redirectTo: 'dances', pathMatch: 'full' },
  { path: 'login', loadComponent: () => import('./pages/login/login.component').then(m => m.LoginComponent) },
  { path: 'dances', loadComponent: () => import('./pages/dances/dances.component').then(m => m.DancesComponent) },
  { path: 'dances/:slug', loadComponent: () => import('./pages/dance-detail/dance-detail.component').then(m => m.DanceDetailComponent) },
  { path: 'profile', loadComponent: () => import('./pages/profile/profile.component').then(m => m.ProfileComponent), canActivate: [authGuard] },
  { path: 'my-dances', loadComponent: () => import('./pages/my-dances/my-dances.component').then(m => m.MyDancesComponent), canActivate: [authGuard] },
  { path: 'practice', loadComponent: () => import('./pages/practice/practice.component').then(m => m.PracticeComponent), canActivate: [authGuard] },
  { path: 'users/:username', loadComponent: () => import('./pages/user-profile/user-profile.component').then(m => m.UserProfileComponent) },
  { path: '**', loadComponent: () => import('./pages/not-found/not-found.component').then(m => m.NotFoundComponent) }
];
