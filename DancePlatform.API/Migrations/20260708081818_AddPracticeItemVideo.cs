using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

namespace DancePlatform.API.Migrations
{
    /// <inheritdoc />
    public partial class AddPracticeItemVideo : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.AddColumn<int>(
                name: "VideoId",
                table: "PracticeSessionItems",
                type: "integer",
                nullable: true);

            migrationBuilder.CreateIndex(
                name: "IX_PracticeSessionItems_VideoId",
                table: "PracticeSessionItems",
                column: "VideoId");

            migrationBuilder.AddForeignKey(
                name: "FK_PracticeSessionItems_Videos_VideoId",
                table: "PracticeSessionItems",
                column: "VideoId",
                principalTable: "Videos",
                principalColumn: "Id",
                onDelete: ReferentialAction.SetNull);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropForeignKey(
                name: "FK_PracticeSessionItems_Videos_VideoId",
                table: "PracticeSessionItems");

            migrationBuilder.DropIndex(
                name: "IX_PracticeSessionItems_VideoId",
                table: "PracticeSessionItems");

            migrationBuilder.DropColumn(
                name: "VideoId",
                table: "PracticeSessionItems");
        }
    }
}
