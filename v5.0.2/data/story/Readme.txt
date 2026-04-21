The JSON format for story scenes looks like this:

{
	"version": 1,
	"press_a_to_advance": true,
	"text": [
		"*3This is a text line. ",
		"Each line is simply concatenated by default.\n",
		"Insert a new line sequence with \n to add a new line anywhere.\n",
		"Use an asterisk *2 to change the size of the text box.\n",
		"The first image aka my_image1.png is used as the background to start.\n",
		"Insert an up carat aka ^ to advance to the next background image\n",
		"in the list below at any time.\n",
		"Add a hashmark aka # to pause for dramatic effect any time.\n",
		"Add multiple hashmarks for a longer pause...##### Like that.\n",
		"Each line of text should fit 80 characters. Blah blah blah blah blah blah blah.\n",
		"The story ends when the last line is printed."
	],
	"images": [
		"my_image1.png",
		"my_image2.png"
	]
}

If you miss a comma anywhere, or some other necessary punctuation mark, the story won't load.

Have fun.
