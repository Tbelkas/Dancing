import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { adminGuard } from './core/guards/admin.guard';
import { unsavedChangesGuard } from './core/guards/unsaved-changes.guard';
import { landingGuard } from './core/guards/landing.guard';
import { personalRoadmapsGuard } from './core/guards/personal-roadmaps.guard';

export const routes: Routes = [
  { path: '', title: 'Dance Platform · Learn any dance, one loop at a time', loadComponent: () => import('./pages/landing/landing.component').then(m => m.LandingComponent), canActivate: [landingGuard] },
  { path: 'login', title: 'Sign in · Dance Platform', loadComponent: () => import('./pages/login/login.component').then(m => m.LoginComponent) },
  { path: 'register', title: 'Create account · Dance Platform', loadComponent: () => import('./pages/login/login.component').then(m => m.LoginComponent) },
  // Both ends of password recovery. No guard on either: the user is by definition signed out.
  { path: 'forgot-password', title: 'Reset your password · Dance Platform', loadComponent: () => import('./pages/password-reset/password-reset.component').then(m => m.PasswordResetComponent) },
  { path: 'reset-password', title: 'Choose a new password · Dance Platform', loadComponent: () => import('./pages/password-reset/password-reset.component').then(m => m.PasswordResetComponent) },
  // Where a provider's callback sends the browser back to. No guard: the whole point is that the
  // user isn't authenticated yet when they arrive.
  { path: 'auth/callback', title: 'Signing in · Dance Platform', loadComponent: () => import('./pages/auth-callback/auth-callback.component').then(m => m.AuthCallbackComponent) },
  { path: 'finish-signup', title: 'Pick your username · Dance Platform', loadComponent: () => import('./pages/finish-signup/finish-signup.component').then(m => m.FinishSignupComponent) },
  { path: 'terms', title: 'Terms of use · Dance Platform', loadComponent: () => import('./pages/legal/legal.component').then(m => m.LegalComponent) },
  { path: 'privacy', title: 'Privacy · Dance Platform', loadComponent: () => import('./pages/legal/legal.component').then(m => m.LegalComponent) },
  { path: 'dances', title: 'Browse Dances · Dance Platform', loadComponent: () => import('./pages/dances/dances.component').then(m => m.DancesComponent) },
  { path: 'roadmaps', title: 'Roadmaps · Dance Platform', loadComponent: () => import('./pages/roadmaps/roadmaps.component').then(m => m.RoadmapsComponent) },
  // Ahead of ':slug', or "new" resolves as a roadmap slug and 404s.
  { path: 'roadmaps/new', title: 'New skill tree · Dance Platform', loadComponent: () => import('./pages/roadmap-builder/roadmap-builder.component').then(m => m.RoadmapBuilderComponent), canActivate: [personalRoadmapsGuard, authGuard], canDeactivate: [unsavedChangesGuard] },
  { path: 'roadmaps/:slug/edit', loadComponent: () => import('./pages/roadmap-builder/roadmap-builder.component').then(m => m.RoadmapBuilderComponent), canActivate: [personalRoadmapsGuard, authGuard], canDeactivate: [unsavedChangesGuard] },
  { path: 'roadmaps/:slug', loadComponent: () => import('./pages/roadmap-detail/roadmap-detail.component').then(m => m.RoadmapDetailComponent) },
  { path: 'dances/:style/:slug', loadComponent: () => import('./pages/dance-detail/dance-detail.component').then(m => m.DanceDetailComponent) },
  { path: 'dances/:slug', loadComponent: () => import('./pages/dance-detail/dance-detail.component').then(m => m.DanceDetailComponent) },
  { path: 'profile', title: 'My Profile · Dance Platform', loadComponent: () => import('./pages/profile/profile.component').then(m => m.ProfileComponent), canActivate: [authGuard] },
  { path: 'my-dances', title: 'My Dances · Dance Platform', loadComponent: () => import('./pages/my-dances/my-dances.component').then(m => m.MyDancesComponent), canActivate: [authGuard] },
  { path: 'library', title: 'Added Videos · Dance Platform', loadComponent: () => import('./pages/library/library.component').then(m => m.LibraryComponent), canActivate: [authGuard] },
  { path: 'choreos', title: 'My Choreos · Dance Platform', loadComponent: () => import('./pages/my-choreos/my-choreos.component').then(m => m.MyChoreosComponent), canActivate: [authGuard] },
  { path: 'practice', title: 'Practice Log · Dance Platform', loadComponent: () => import('./pages/practice/practice.component').then(m => m.PracticeComponent), canActivate: [authGuard] },
  { path: 'admin/review', title: 'Review queue · Dance Platform', loadComponent: () => import('./pages/admin-review/admin-review.component').then(m => m.AdminReviewComponent), canActivate: [adminGuard] },
  { path: 'admin/add-video', title: 'Add Video · Dance Platform', loadComponent: () => import('./pages/admin-add-video/admin-add-video.component').then(m => m.AdminAddVideoComponent), canActivate: [adminGuard] },
  { path: 'users/:username', loadComponent: () => import('./pages/user-profile/user-profile.component').then(m => m.UserProfileComponent) },
  { path: '**', title: 'Page not found · Dance Platform', loadComponent: () => import('./pages/not-found/not-found.component').then(m => m.NotFoundComponent) }
];
