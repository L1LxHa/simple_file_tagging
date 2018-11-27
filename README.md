## Simple file tagging.

The tags are stored in file names. Here are the characteristics of this approach:
  * Cons:
     * The amount/length of the tags is hard-limited by the given filesystem's
       max filename length.
     * Easy to lose information when moving files between filesystems with different
       filename lengths.
  * Pros:
     * Very simple.
     * No possibility of tags getting lost - they're always attached to the file.
     * Can be manually edited without needing special tools or knowledge.
     * Standard UNIX tools work great, e.g. grep.

Example file name without tags:
  * 'Picture 002.jpg'
And with:
  * 'Picture 002 #flowers #flying-whales #wallpaper.jpg'
