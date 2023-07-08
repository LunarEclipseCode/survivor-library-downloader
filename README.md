# Survivor Library Downloader

Download the latest version of the program [here](https://github.com/LunarEclipseCode/survivor-library-downloader/releases/) 

![image](https://github.com/LunarEclipseCode/survivor-library-downloader/assets/74882728/25bf862e-17b4-42f8-831d-39b2e145b84f)

Although the name says 'Downloader', The purpose of this program is more than just creating an offline copy of the [Survivor Library](https://www.survivorlibrary.com/library-download.html). 

These are a couple of quirks and features of the program.

1. Let's say you are downloading files using the program, and suddenly your PC crashes or a power outage occurs. When you run the program next time and select the topics you were downloading, you can enable 'Check for Corrupted Files' and the program will delete the corrupted files and download fresh copies. More about this topic is discussed later.

2. This is a multi-threaded application which allows really fast link retrieval. Theoretically, If you select all the topics, the program will retrieve download links to all books from 150+ categories in under 15 seconds.

3. To easily select multiple categories at once, if you select two categories while holding the Shift key, all categories between them will be selected too.

4. There is even a dark mode!!

5. Let's say you have finished downloading books from categories that interest you. Now, six months later, if you select those topics and run the program again, it will only download files that have been added in the last six months under those categories. In simple words, if you already have the file, the application will not download it again.

6. You can keep the file names like the default format 'accounting_principles_1917.pdf' or check the 'Rename Files' checkbox and name them as 'Accounting Principles 1917.pdf.'' Even if you have a mix of both naming conventions, it will not affect the 'auto-update' feature mentioned in #5.

7. The application also checks if you have enough storage left before downloading,

### Details about Corrupted File Checking:

The program has two forms of checking for corrupted files:

1. After downloading a pdf from Survivor Library, the program checks if the file is corrupted or not. If the file is corrupted, it is deleted. Currently, these are the only corrupted files in Survivor Library out of over 14,000 files.
   
   | Category                       | Corrupted Files                                                                                                                                                                                                                                                                                                                                                  |
   |:------------------------------:|:----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------:|
   | Astronomy                      | The Telescope-Nott 1832<br/>Youths Book of Astronomy 1838                                                                                                                                                                                                                                                                                                        |
   | Farming2                       | Farm Friends and Farm Foes-A Text-book of Agricultural Science 1910                                                                                                                                                                                                                                                                                              |
   | Firearms-Manuals               | Savage CUB BOLT ACTION RIFLE                                                                                                                                                                                                                                                                                                                                     |
   | Scientific American (Series 1) | Scientific American 1853-05-07 Vol-08 Issue-34<br/>Scientific American 1853-09-10 Vol-08 Issue-52<br/>Scientific American 1856-06-07 Vol-11 Issue-39<br/>Scientific American 1857-12-26 Vol-13 Issue-16<br/>Scientific American 1858-02-13 Vol-13 Issue-23<br/>Scientific American 1857-10-31 Vol-13 Issue-08<br/>Scientific American 1858-09-04 Vol-13 Issue-52 |
   | Scientific American (Series 2) | Scientific American 1874-09-12 Vol-31 Issue-11<br/>Scientific American 1876-01-29 Vol-34 Issue-06                                                                                                                                                                                                                                                                |
   | Shoemaking                     | Hygiene of the Boot and Shoe Industry in Massachusetts 1912                                                                                                                                                                                                                                                                                                      |
   | Survival - Individual          | Nuclear War Survival Skills September 1979                                                                                                                                                                                                                                                                                                                       |
   | Teaching - Civics              | A Text Book of Civics for the State of Washington 1910                                                                                                                                                                                                                                                                                                           |

2. If the checkbox 'Check for Corrupted Files' is enabled, the program will delete the corrupted files on your PC in your selected categories and download fresh copies. Now let's consider some scenarios.
   
   1. If you are downloading certain categories for the first time, it doesn't matter whether you enable or disable it because there are no files to check.
   
   2. You have downloaded from 20 categories a year ago. Now, you want to check whether any new files were added. If you used this application to download those files a year ago, you don't need to check for corrupted files because after downloading each file, the application automatically checks for it.
      
      However, even if you enable it, it's not a big deal. It will take 2-3 minutes if you have a hard drive, and much faster if you have SSD.
   
   3. Now, if you have the entire Survivor Library downloaded and want to update your offline copy a year later, then again, if you used this application to download those files a year ago, you don't need to check for corrupted files.
      
      However, if you do check all the files, it will take some time, especially if the data is stored on a hard drive. From my testing, to check about 12,000 files (close to 200 GB), it takes about 35 minutes on a hard drive. I didn't test it on SSD, but I expect the speed to be much faster.
   
   So, the bottom line is, unless this application or Windows crashes, you really don't need to enable the 'Check for Corrupted Files' option.

### Plan for Future Versions:

1. Ability to pause and resume downloads.

2. Change all your files to a particular naming convention.

If you would like to have any other feature or have encountered any bugs, please let me know.
