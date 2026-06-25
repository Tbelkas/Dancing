using System;
using Microsoft.EntityFrameworkCore.Migrations;
using Npgsql.EntityFrameworkCore.PostgreSQL.Metadata;

#nullable disable

namespace DancePlatform.API.Migrations
{
    /// <inheritdoc />
    public partial class WindowedPracticeSessions : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            // The old PracticeSessions row was one dance + duration; the new shape is a windowed
            // session whose dances live in PracticeSessionItems. Migrate existing rows rather than
            // drop them: reuse DateAdded as StartedAt, copy each (DanceId, DurationMinutes) into an
            // item, then retire the now-redundant columns.

            migrationBuilder.RenameColumn(
                name: "DateAdded",
                table: "PracticeSessions",
                newName: "StartedAt");

            migrationBuilder.AddColumn<DateTime>(
                name: "LastActivityAt",
                table: "PracticeSessions",
                type: "timestamp with time zone",
                nullable: true);

            migrationBuilder.Sql(
                "UPDATE \"PracticeSessions\" SET \"LastActivityAt\" = \"StartedAt\";");

            // Every row was just backfilled from StartedAt, so the column can go NOT NULL with no default.
            migrationBuilder.AlterColumn<DateTime>(
                name: "LastActivityAt",
                table: "PracticeSessions",
                type: "timestamp with time zone",
                nullable: false,
                oldClrType: typeof(DateTime),
                oldType: "timestamp with time zone",
                oldNullable: true);

            migrationBuilder.CreateTable(
                name: "PracticeSessionItems",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    PracticeSessionId = table.Column<int>(type: "integer", nullable: false),
                    DanceId = table.Column<int>(type: "integer", nullable: false),
                    Seconds = table.Column<int>(type: "integer", nullable: false),
                    Notes = table.Column<string>(type: "text", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_PracticeSessionItems", x => x.Id);
                    table.ForeignKey(
                        name: "FK_PracticeSessionItems_Dances_DanceId",
                        column: x => x.DanceId,
                        principalTable: "Dances",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "FK_PracticeSessionItems_PracticeSessions_PracticeSessionId",
                        column: x => x.PracticeSessionId,
                        principalTable: "PracticeSessions",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            // Carry each legacy single-dance session over as one item (minutes -> seconds).
            migrationBuilder.Sql(
                "INSERT INTO \"PracticeSessionItems\" (\"PracticeSessionId\", \"DanceId\", \"Seconds\", \"Notes\") " +
                "SELECT \"Id\", \"DanceId\", COALESCE(\"DurationMinutes\", 0) * 60, NULL " +
                "FROM \"PracticeSessions\";");

            // Old per-session dance columns are now superseded by the items table.
            migrationBuilder.DropForeignKey(
                name: "FK_PracticeSessions_Dances_DanceId",
                table: "PracticeSessions");

            migrationBuilder.DropIndex(
                name: "IX_PracticeSessions_DanceId",
                table: "PracticeSessions");

            migrationBuilder.DropIndex(
                name: "IX_PracticeSessions_UserId",
                table: "PracticeSessions");

            migrationBuilder.DropColumn(
                name: "DanceId",
                table: "PracticeSessions");

            migrationBuilder.DropColumn(
                name: "DurationMinutes",
                table: "PracticeSessions");

            migrationBuilder.CreateIndex(
                name: "IX_PracticeSessions_UserId_LastActivityAt",
                table: "PracticeSessions",
                columns: new[] { "UserId", "LastActivityAt" });

            migrationBuilder.CreateIndex(
                name: "IX_PracticeSessionItems_DanceId",
                table: "PracticeSessionItems",
                column: "DanceId");

            migrationBuilder.CreateIndex(
                name: "IX_PracticeSessionItems_PracticeSessionId_DanceId",
                table: "PracticeSessionItems",
                columns: new[] { "PracticeSessionId", "DanceId" });
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "PracticeSessionItems");

            migrationBuilder.DropIndex(
                name: "IX_PracticeSessions_UserId_LastActivityAt",
                table: "PracticeSessions");

            migrationBuilder.DropColumn(
                name: "LastActivityAt",
                table: "PracticeSessions");

            migrationBuilder.RenameColumn(
                name: "StartedAt",
                table: "PracticeSessions",
                newName: "DateAdded");

            migrationBuilder.AddColumn<int>(
                name: "DanceId",
                table: "PracticeSessions",
                type: "integer",
                nullable: false,
                defaultValue: 0);

            migrationBuilder.AddColumn<int>(
                name: "DurationMinutes",
                table: "PracticeSessions",
                type: "integer",
                nullable: true);

            migrationBuilder.CreateIndex(
                name: "IX_PracticeSessions_DanceId",
                table: "PracticeSessions",
                column: "DanceId");

            migrationBuilder.CreateIndex(
                name: "IX_PracticeSessions_UserId",
                table: "PracticeSessions",
                column: "UserId");

            migrationBuilder.AddForeignKey(
                name: "FK_PracticeSessions_Dances_DanceId",
                table: "PracticeSessions",
                column: "DanceId",
                principalTable: "Dances",
                principalColumn: "Id",
                onDelete: ReferentialAction.Cascade);
        }
    }
}
