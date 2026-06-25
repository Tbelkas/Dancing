using System;
using Microsoft.EntityFrameworkCore.Migrations;
using Npgsql.EntityFrameworkCore.PostgreSQL.Metadata;

#nullable disable

namespace DancePlatform.API.Migrations
{
    /// <inheritdoc />
    public partial class AddUserVideoLoops : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "UserVideoLoops",
                columns: table => new
                {
                    Id = table.Column<int>(type: "integer", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    UserId = table.Column<int>(type: "integer", nullable: false),
                    VideoId = table.Column<int>(type: "integer", nullable: false),
                    Label = table.Column<string>(type: "text", nullable: false),
                    StartTime = table.Column<int>(type: "integer", nullable: false),
                    EndTime = table.Column<int>(type: "integer", nullable: true),
                    DateAdded = table.Column<DateTime>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("PK_UserVideoLoops", x => x.Id);
                    table.ForeignKey(
                        name: "FK_UserVideoLoops_Users_UserId",
                        column: x => x.UserId,
                        principalTable: "Users",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "FK_UserVideoLoops_Videos_VideoId",
                        column: x => x.VideoId,
                        principalTable: "Videos",
                        principalColumn: "Id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateIndex(
                name: "IX_UserVideoLoops_UserId_VideoId",
                table: "UserVideoLoops",
                columns: new[] { "UserId", "VideoId" });

            migrationBuilder.CreateIndex(
                name: "IX_UserVideoLoops_VideoId",
                table: "UserVideoLoops",
                column: "VideoId");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "UserVideoLoops");
        }
    }
}
