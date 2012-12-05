@
@ Copyright 2011: dogbert <dogber1@gmail.com>
@
@ This program is free software; you can redistribute it and/or modify
@ it under the terms of the GNU General Public License as published by
@ the Free Software Foundation; either version 2 of the License, or
@ (at your option) any later version.
@
@ This program is distributed in the hope that it will be useful,
@ but WITHOUT ANY WARRANTY; without even the implied warranty of
@ MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
@ GNU General Public License for more details.
@
@ You should have received a copy of the GNU General Public License
@ along with this program; if not, write to the Free Software
@ Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
@

.align 4
.thumb_func

	push	{LR}
	sub	R4,#28
	ldmia	R4!,{r0-r2}
	blx	R2 	@allocPktBuf
	push	{R0}
	ldmia	R4!,{r0-r1}
	blx	R1 	@heap_alloc
	ldr	R1,[SP]
	add	R1,#1
	str	R0,[R1]
	ldmia	R4!,{r1-r2}
	blx	R2 	@readSFS
	pop	{R0,PC}
