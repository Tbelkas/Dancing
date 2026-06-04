using DancePlatform.API.Models;
using Microsoft.EntityFrameworkCore;

namespace DancePlatform.API.Data;

public class AppDbContext : DbContext
{
    public AppDbContext(DbContextOptions<AppDbContext> options) : base(options) { }

    public DbSet<User> Users => Set<User>();
    public DbSet<Dance> Dances => Set<Dance>();
    public DbSet<Style> Styles => Set<Style>();
    public DbSet<MusicalStyle> MusicalStyles => Set<MusicalStyle>();
    public DbSet<Video> Videos => Set<Video>();
    public DbSet<DanceStyle> DanceStyles => Set<DanceStyle>();
    public DbSet<DanceMusicalStyle> DanceMusicalStyles => Set<DanceMusicalStyle>();
    public DbSet<UserFavoriteDance> UserFavoriteDances => Set<UserFavoriteDance>();
    public DbSet<UserLearnedDance> UserLearnedDances => Set<UserLearnedDance>();
    public DbSet<UserInProgressDance> UserInProgressDances => Set<UserInProgressDance>();
    public DbSet<UserMyStyle> UserMyStyles => Set<UserMyStyle>();
    public DbSet<DanceRating> DanceRatings => Set<DanceRating>();
    public DbSet<PracticeSession> PracticeSessions => Set<PracticeSession>();
    public DbSet<Instructor> Instructors => Set<Instructor>();
    public DbSet<DanceInstructor> DanceInstructors => Set<DanceInstructor>();

    protected override void OnModelCreating(ModelBuilder modelBuilder)
    {
        modelBuilder.Entity<DanceStyle>()
            .HasKey(ds => new { ds.DanceId, ds.StyleId });

        modelBuilder.Entity<DanceStyle>()
            .HasOne(ds => ds.Dance)
            .WithMany(d => d.DanceStyles)
            .HasForeignKey(ds => ds.DanceId);

        modelBuilder.Entity<DanceStyle>()
            .HasOne(ds => ds.Style)
            .WithMany(s => s.DanceStyles)
            .HasForeignKey(ds => ds.StyleId);

        modelBuilder.Entity<DanceMusicalStyle>()
            .HasKey(dms => new { dms.DanceId, dms.MusicalStyleId });

        modelBuilder.Entity<DanceMusicalStyle>()
            .HasOne(dms => dms.Dance)
            .WithMany(d => d.DanceMusicalStyles)
            .HasForeignKey(dms => dms.DanceId);

        modelBuilder.Entity<DanceMusicalStyle>()
            .HasOne(dms => dms.MusicalStyle)
            .WithMany(ms => ms.DanceMusicalStyles)
            .HasForeignKey(dms => dms.MusicalStyleId);

        modelBuilder.Entity<UserFavoriteDance>()
            .HasKey(ufd => new { ufd.UserId, ufd.DanceId });

        modelBuilder.Entity<UserFavoriteDance>()
            .HasOne(ufd => ufd.User)
            .WithMany(u => u.FavoriteDances)
            .HasForeignKey(ufd => ufd.UserId);

        modelBuilder.Entity<UserFavoriteDance>()
            .HasOne(ufd => ufd.Dance)
            .WithMany(d => d.FavoritedBy)
            .HasForeignKey(ufd => ufd.DanceId);

        modelBuilder.Entity<UserLearnedDance>()
            .HasKey(uld => new { uld.UserId, uld.DanceId });

        modelBuilder.Entity<UserLearnedDance>()
            .HasOne(uld => uld.User)
            .WithMany(u => u.LearnedDances)
            .HasForeignKey(uld => uld.UserId);

        modelBuilder.Entity<UserLearnedDance>()
            .HasOne(uld => uld.Dance)
            .WithMany(d => d.LearnedBy)
            .HasForeignKey(uld => uld.DanceId);

        modelBuilder.Entity<UserInProgressDance>()
            .HasKey(uid => new { uid.UserId, uid.DanceId });

        modelBuilder.Entity<UserInProgressDance>()
            .HasOne(uid => uid.User)
            .WithMany(u => u.InProgressDances)
            .HasForeignKey(uid => uid.UserId);

        modelBuilder.Entity<UserInProgressDance>()
            .HasOne(uid => uid.Dance)
            .WithMany(d => d.InProgressBy)
            .HasForeignKey(uid => uid.DanceId);

        modelBuilder.Entity<UserMyStyle>()
            .HasKey(ums => new { ums.UserId, ums.StyleId });

        modelBuilder.Entity<UserMyStyle>()
            .HasOne(ums => ums.User)
            .WithMany(u => u.MyStyles)
            .HasForeignKey(ums => ums.UserId);

        modelBuilder.Entity<UserMyStyle>()
            .HasOne(ums => ums.Style)
            .WithMany(s => s.MyStyleUsers)
            .HasForeignKey(ums => ums.StyleId);

        modelBuilder.Entity<User>()
            .HasIndex(u => u.Username)
            .IsUnique();

        modelBuilder.Entity<DanceRating>()
            .HasKey(dr => new { dr.UserId, dr.DanceId });

        modelBuilder.Entity<DanceRating>()
            .HasOne(dr => dr.User)
            .WithMany(u => u.Ratings)
            .HasForeignKey(dr => dr.UserId)
            .OnDelete(DeleteBehavior.Cascade);

        modelBuilder.Entity<DanceRating>()
            .HasOne(dr => dr.Dance)
            .WithMany(d => d.Ratings)
            .HasForeignKey(dr => dr.DanceId)
            .OnDelete(DeleteBehavior.Cascade);

        modelBuilder.Entity<PracticeSession>()
            .HasOne(ps => ps.User)
            .WithMany(u => u.PracticeSessions)
            .HasForeignKey(ps => ps.UserId)
            .OnDelete(DeleteBehavior.Cascade);

        modelBuilder.Entity<PracticeSession>()
            .HasOne(ps => ps.Dance)
            .WithMany(d => d.PracticeSessions)
            .HasForeignKey(ps => ps.DanceId)
            .OnDelete(DeleteBehavior.Cascade);

        modelBuilder.Entity<DanceInstructor>()
            .HasKey(di => new { di.DanceId, di.InstructorId });

        modelBuilder.Entity<DanceInstructor>()
            .HasOne(di => di.Dance)
            .WithMany(d => d.DanceInstructors)
            .HasForeignKey(di => di.DanceId)
            .OnDelete(DeleteBehavior.Cascade);

        modelBuilder.Entity<DanceInstructor>()
            .HasOne(di => di.Instructor)
            .WithMany(i => i.DanceInstructors)
            .HasForeignKey(di => di.InstructorId)
            .OnDelete(DeleteBehavior.Restrict);
    }
}
