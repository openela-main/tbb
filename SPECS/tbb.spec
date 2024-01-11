%global upver 2018
%global uprel 2

Name:    tbb
Summary: The Threading Building Blocks library abstracts low-level threading details
Version: %{upver}%{?uprel:.%{uprel}}
Release: 9%{?dist}
License: ASL 2.0
Group:   Development/Tools
URL:     http://threadingbuildingblocks.org/

Source0: https://github.com/01org/tbb/archive/%{upver}%{?uprel:_U%{uprel}}.tar.gz
# These three are downstream sources.
Source6: tbb.pc
Source7: tbbmalloc.pc
Source8: tbbmalloc_proxy.pc

# Propagate CXXFLAGS variable into flags used when compiling C++.
# This is so that RPM_OPT_FLAGS are respected.
Patch1: tbb-4.4-cxxflags.patch

# For 32-bit x86 only, don't assume that the mfence instruction is available.
# It was added with SSE2.  This patch causes a lock xchg instruction to be
# emitted for non-SSE2 builds, and the mfence instruction to be emitted for
# SSE2-enabled builds.
Patch2: tbb-4.0-mfence.patch

# Don't snip -Wall from C++ flags.  Add -fno-strict-aliasing, as that
# uncovers some static-aliasing warnings.
# Related: https://bugzilla.redhat.com/show_bug.cgi?id=1037347
Patch3: tbb-4.3-dont-snip-Wall.patch

# python3 is not available on RHEL <=7
%if 0%{?rhel} && 0%{?rhel} <= 7
# disable python3 by default
%bcond_with python3
%else
%bcond_without python3
%endif

# python2 is not available on RHEL > 7 and not needed on Fedora > 28
%if 0%{?rhel} > 7 || 0%{?fedora} > 28
# disable python2 by default
%bcond_with python2
%else
%bcond_without python2
%endif

BuildRequires: gcc-c++
BuildRequires: swig

%if %{with python2}
BuildRequires: python2-devel
%endif

%if %{with python3}
BuildRequires: python3-devel
%endif

%description
Threading Building Blocks (TBB) is a C++ runtime library that
abstracts the low-level threading details necessary for optimal
multi-core performance.  It uses common C++ templates and coding style
to eliminate tedious threading implementation work.

TBB requires fewer lines of code to achieve parallelism than other
threading models.  The applications you write are portable across
platforms.  Since the library is also inherently scalable, no code
maintenance is required as more processor cores become available.


%package devel
Summary: The Threading Building Blocks C++ headers and shared development libraries
Group: Development/Libraries
Requires: %{name}%{?_isa} = %{version}-%{release}

%description devel
Header files and shared object symlinks for the Threading Building
Blocks (TBB) C++ libraries.


%package doc
Summary: The Threading Building Blocks documentation
Group: Documentation
Provides: bundled(jquery)

%description doc
PDF documentation for the user of the Threading Building Block (TBB)
C++ library.

%if %{with python2}
%package -n python2-%{name}
Summary: Python 2 TBB module
%{?python_provide:%python_provide python2-%{name}}
Requires: tbb = %{version}-%{release}

%description -n python2-%{name}
Python 2 TBB module.
%endif

%if %{with python3}
%package -n python3-%{name}
Summary: Python 3 TBB module
%{?python_provide:%python_provide python3-%{name}}
Requires: tbb = %{version}-%{release}

%description -n python3-%{name}
Python 3 TBB module.
%endif

%prep
%setup -q -n %{name}-%{upver}_U%{uprel}
%patch1 -p1
%patch2 -p1
%patch3 -p1

# For repeatable builds, don't query the hostname or architecture
sed -i 's/"`hostname -s`" ("`uname -m`"/fedorabuild (%{_arch}/' \
    build/version_info_linux.sh

# Do not assume the RTM instructions are available
sed -i 's/-mrtm//' build/linux.gcc.inc

%if %{with python2}
# Invoke the right python binary directly
sed -i 's,env python,python2,' python/TBB.py python/tbb/__*.py
%endif

%if %{with python3}
# Invoke the right python binary directly
sed -i 's,env python,python3,' python/TBB.py python/tbb/__*.py
%endif

# Remove shebang from files that don't need it
sed -i '/^#!/d' python/tbb/{pool,test}.py

# Fix libdir on 64-bit systems
if [ "%{_libdir}" != "%{_prefix}/lib" ]; then
  sed -i.orig 's/"lib"/"%{_lib}"/' cmake/TBBMakeConfig.cmake
  touch -r cmake/TBBMakeConfig.cmake.orig cmake/TBBMakeConfig.cmake
  rm cmake/TBBMakeConfig.cmake.orig
fi

# Prepare to build the python module for both python 2 and python 3
%if %{with python2}
cp -a python python2
%endif

%if %{with python3}
cp -a python python3
sed -i 's,python,python3,g' python3/Makefile python3/rml/Makefile
sed -i 's,python2,python3,' python3/TBB.py python3/tbb/__*.py
%endif

# Invoke Python with the %%{__python3} executable instead of hardcoded python3
sed -i 's,PY_SETUP=python3,PY_SETUP=%{__python3},g' python3/Makefile
sed -i 's,python3 -m tbb test,%{__python3} -m tbb test,g' python3/Makefile

%build
%ifarch %{ix86}
# Build an SSE2-enabled version so the mfence instruction can be used
cp -a build build.orig
make %{?_smp_mflags} tbb_build_prefix=obj stdver=c++14 \
  CXXFLAGS="$RPM_OPT_FLAGS -march=pentium4 -msse2" \
  LDFLAGS="-Wl,--as-needed $RPM_LD_FLAGS"
mv build build.sse2
mv build.orig build
%endif

make %{?_smp_mflags} tbb_build_prefix=obj stdver=c++14 \
  CXXFLAGS="$RPM_OPT_FLAGS" \
  LDFLAGS="-Wl,--as-needed $RPM_LD_FLAGS"
for file in %{SOURCE6} %{SOURCE7} %{SOURCE8}; do
    base=$(basename ${file})
    sed 's/_FEDORA_VERSION/%{version}/' ${file} > ${base}
    touch -r ${file} ${base}
done

# Build for python 2
%if %{with python2}
. build/obj_release/tbbvars.sh
pushd python2
make %{?_smp_mflags} -C rml stdver=c++14 \
  CPLUS_FLAGS="%{optflags} -DDO_ITT_NOTIFY -DUSE_PTHREAD" \
  PIC_KEY="-fPIC -Wl,--as-needed" \
  LDFLAGS="$RPM_LD_FLAGS"
cp -p rml/libirml.so* .
%py2_build
popd
%endif

%if %{with python3}
# Build for python 3
. build/obj_release/tbbvars.sh
pushd python3
make %{?_smp_mflags} -C rml stdver=c++14 \
  CPLUS_FLAGS="%{optflags} -DDO_ITT_NOTIFY -DUSE_PTHREAD" \
  PIC_KEY="-fPIC -Wl,--as-needed" \
  LDFLAGS="$RPM_LD_FLAGS"
cp -p rml/libirml.so* .
%py3_build
popd
%endif


%check
echo ============BEGIN TESTING===============
make -k test tbb_build_prefix=obj stdver=c++14 CXXFLAGS="$RPM_OPT_FLAGS" && true
echo ============END TESTING===========

%install
mkdir -p $RPM_BUILD_ROOT/%{_libdir}
mkdir -p $RPM_BUILD_ROOT/%{_includedir}

%ifarch %{ix86}
mkdir -p $RPM_BUILD_ROOT/%{_libdir}/sse2
pushd build.sse2/obj_release
    for file in libtbb{,malloc{,_proxy}}; do
        install -p -D -m 755 ${file}.so.2 $RPM_BUILD_ROOT/%{_libdir}/sse2
    done
popd
%endif

pushd build/obj_release
    for file in libtbb{,malloc{,_proxy}}; do
        install -p -D -m 755 ${file}.so.2 $RPM_BUILD_ROOT/%{_libdir}
        ln -s $file.so.2 $RPM_BUILD_ROOT/%{_libdir}/$file.so
    done
popd

pushd include
    find tbb -type f ! -name \*.htm\* -exec \
        install -p -D -m 644 {} $RPM_BUILD_ROOT/%{_includedir}/{} \
    \;
popd

for file in %{SOURCE6} %{SOURCE7} %{SOURCE8}; do
    install -p -D -m 644 $(basename ${file}) \
        $RPM_BUILD_ROOT/%{_libdir}/pkgconfig/$(basename ${file})
done

# Install the rml headers
mkdir -p $RPM_BUILD_ROOT%{_includedir}/rml
cp -p src/rml/include/*.h $RPM_BUILD_ROOT%{_includedir}/rml

# Python 2 install
%if %{with python2}
. build/obj_release/tbbvars.sh
pushd python
%py2_install
chmod a+x $RPM_BUILD_ROOT%{python2_sitearch}/TBB.py
chmod a+x $RPM_BUILD_ROOT%{python2_sitearch}/tbb/__*.py
cp -p libirml.so.1 $RPM_BUILD_ROOT%{_libdir}
ln -s libirml.so.1 $RPM_BUILD_ROOT%{_libdir}/libirml.so
popd
%endif

# Python 3 install
%if %{with python3}
pushd python3
%py3_install
chmod a+x $RPM_BUILD_ROOT%{python3_sitearch}/TBB.py
chmod a+x $RPM_BUILD_ROOT%{python3_sitearch}/tbb/__*.py
cp -p libirml.so.1 $RPM_BUILD_ROOT%{_libdir}
ln -s libirml.so.1 $RPM_BUILD_ROOT%{_libdir}/libirml.so
popd
%endif

# Install the cmake files
mkdir -p $RPM_BUILD_ROOT%{_libdir}/cmake
cp -a cmake $RPM_BUILD_ROOT%{_libdir}/cmake/%{name}
rm $RPM_BUILD_ROOT%{_libdir}/cmake/%{name}/README.rst

%post -p /sbin/ldconfig

%postun -p /sbin/ldconfig

%files
%doc doc/Release_Notes.txt README.md
%license LICENSE
%{_libdir}/*.so.2
%{_libdir}/libirml.so.1
%ifarch %{ix86}
%{_libdir}/sse2/*.so.2
%endif

%files devel
%doc CHANGES cmake/README.rst
%{_includedir}/rml
%{_includedir}/tbb
%{_libdir}/*.so
%{_libdir}/cmake/
%{_libdir}/pkgconfig/*.pc

%files doc
%doc doc/Release_Notes.txt
%doc doc/html

%if %{with python2}
%files -n python2-%{name}
%doc python/index.html
%{python2_sitearch}/TBB*
%{python2_sitearch}/tbb/
%endif

%if %{with python3}
%files -n python3-%{name}
%doc python3/index.html
%{python3_sitearch}/TBB*
%{python3_sitearch}/tbb/
%{python3_sitearch}/__pycache__/TBB*
%endif

%changelog
* Tue Nov 13 2018 Patsy Griffin Franklin <pfrankli@redhat.com> - 2018.2-9
- Require the correct version of tbb for python2-tbb and python3-tbb.
  (BZ #1638041)

* Fri Sep 28 2018 Patsy Griffin Franklin <pfrankli@redhat.com> - 2018.2-8
- Run check for all supported architectures.

* Wed Aug 01 2018 Patsy Griffin Franklin <pfrankli@redhat.com> - 2018.2-7
- Selectively build python2 or python3 based on current version.
- Don't use pathfix.py as it fails prep on RHEL when building on systems
  do not have python installled.

* Tue Jul 03 2018 Tomas Orsava <torsava@redhat.com> - 2018.2-6
- Switch hardcoded python3 path into the %%{__python3} macro

* Fri Feb 09 2018 Fedora Release Engineering <releng@fedoraproject.org> - 2018.2-5
- Rebuilt for https://fedoraproject.org/wiki/Fedora_28_Mass_Rebuild

* Tue Jan 30 2018 Jerry James <loganjerry@gmail.com> - 2018.2-4
- Build libirml with the correct flags (bz 1540268)
- Do not build with -mrtm

* Mon Jan 29 2018 Iryna Shcherbina <ishcherb@redhat.com> - 2018.2-3
- Fix Python 2 dependency from python3-tbb

* Fri Jan 26 2018 Jerry James <loganjerry@gmail.com> - 2018.2-2
- Install libirml for the python interfaces

* Wed Jan 24 2018 Jerry James <loganjerry@gmail.com> - 2018.2-1
- Rebase to 2018 update 2

* Sat Nov 25 2017 Jerry James <loganjerry@gmail.com> - 2018.1-1
- Rebase to 2018 update 1

* Thu Aug 03 2017 Fedora Release Engineering <releng@fedoraproject.org> - 2017.7-3
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Binutils_Mass_Rebuild

* Thu Jul 27 2017 Fedora Release Engineering <releng@fedoraproject.org> - 2017.7-2
- Rebuilt for https://fedoraproject.org/wiki/Fedora_27_Mass_Rebuild

* Thu Jun  8 2017 Jerry James <loganjerry@gmail.com> - 2017.7-1
- Rebase to 2017 update 7
- Use the license macro
- Ship the new cmake files in -devel

* Tue May 16 2017 Jerry James <loganjerry@gmail.com> - 2017.6-1
- Rebase to 2017 update 6

* Fri Mar 17 2017 Jerry James <loganjerry@gmail.com> - 2017.5-1
- Rebase to 2017 update 5
- Change version scheme again to match upstream's change
- New source URL on github
- Drop upstreamed patch to fix detection of s390x as 64-bit arch

* Sat Feb 11 2017 Fedora Release Engineering <releng@fedoraproject.org> - 2017-8.20161128
- Rebuilt for https://fedoraproject.org/wiki/Fedora_26_Mass_Rebuild

* Mon Jan 02 2017 Dan Horák <dan[at]danny.cz> - 2017-7.20161128
- Fix detection of s390x as 64-bit arch (#1379632)

* Mon Dec 19 2016 Miro Hrončok <mhroncok@redhat.com> - 2017-6.20161128
- Rebuild for Python 3.6

* Fri Dec  2 2016 Jerry James <loganjerry@gmail.com> - 2017-5.20161128
- Rebase to 2017 update 3
- Drop upstreamed s390x patch

* Wed Nov  2 2016 Jerry James <loganjerry@gmail.com> - 2017-4.20161004
- Rebase to 2017 update 2

* Fri Oct 07 2016 Dan Horák <dan[at]danny.cz> - 2017-3.20160916
- Fix detection of s390x as 64-bit arch (#1379632)

* Fri Sep 30 2016 Jerry James <loganjerry@gmail.com> - 2017-2.20160916
- New upstream release

* Thu Sep 22 2016 Jerry James <loganjerry@gmail.com> - 2017-1.20160722
- Rebase to 2017, new upstream version numbering scheme

* Tue Jul 19 2016 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 4.4-8.20160526
- https://fedoraproject.org/wiki/Changes/Automatic_Provides_for_Python_RPM_Packages

* Wed Jun  1 2016 Jerry James <loganjerry@gmail.com> - 4.4-7.20160526
- Rebase to 4.4u5
- Build in C++14 mode
- Build the new python module

* Fri May  6 2016 Jerry James <loganjerry@gmail.com> - 4.4-6.20160413
- Rebase to 4.4u4

* Mon Apr  4 2016 Jerry James <loganjerry@gmail.com> - 4.4-5.20160316
- Add -fno-delete-null-pointer-checks to fix optimized code

* Fri Mar 18 2016 Jerry James <loganjerry@gmail.com> - 4.4-4.20160316
- Updated upstream tarball
- Link with RPM_LD_FLAGS

* Sat Feb 20 2016 Jerry James <loganjerry@gmail.com> - 4.4-3.20160128
- Rebase to 4.4u3

* Fri Feb 05 2016 Fedora Release Engineering <releng@fedoraproject.org> - 4.4-2.20151115
- Rebuilt for https://fedoraproject.org/wiki/Fedora_24_Mass_Rebuild

* Fri Jan 15 2016 Jerry James <loganjerry@gmail.com> - 4.4-1.20151115
- Rebase to 4.4u2
- Fix the mfence patch to actually emit a memory barrier (bz 1288314)
- Build an sse2 version for i386 for better performance on capable CPUs
- Enable use of C++0x features
- Drop out-of-date CHANGES.txt from git

* Fri Jun 19 2015 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 4.3-3.20141204
- Rebuilt for https://fedoraproject.org/wiki/Fedora_23_Mass_Rebuild

* Sat May 02 2015 Kalev Lember <kalevlember@gmail.com> - 4.3-2.20141204
- Rebuilt for GCC 5 C++11 ABI change

* Mon Jan 19 2015 Petr Machata <pmachata@redhat.com> - 4.3-1.20141204
- Rebase to 4.3u2
- Drop ExclusiveArch

* Thu Sep 25 2014 Karsten Hopp <karsten@redhat.com> 4.1-9.20130314
- enable ppc64le and run 'make test' on that new arch

* Mon Aug 18 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 4.1-8.20130314
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_22_Mass_Rebuild

* Sun Jun 08 2014 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 4.1-7.20130314
- Rebuilt for https://fedoraproject.org/wiki/Fedora_21_Mass_Rebuild

* Sun Jan 12 2014 Peter Robinson <pbrobinson@fedoraproject.org> 4.1-6.20130314
- Build on aarch64, minor spec cleanups

* Tue Dec  3 2013 Petr Machata <pmachata@redhat.com> - 4.1-5.20130314
- Fix building with -Werror=format-security (tbb-4.1-dont-snip-Wall.patch)

* Thu Oct  3 2013 Petr Machata <pmachata@redhat.com> - 4.1-4.20130314
- Fix %%install to also install include files that are not named *.h

* Sun Aug 04 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 4.1-3.20130314
- Rebuilt for https://fedoraproject.org/wiki/Fedora_20_Mass_Rebuild

* Tue May 28 2013 Petr Machata <pmachata@redhat.com> - 4.1-3.20130314
- Enable ARM arches

* Wed May 22 2013 Petr Machata <pmachata@redhat.com> - 4.1-2.20130314
- Fix mfence patch.  Since the __TBB_full_memory_fence macro was
  function-call-like, it stole () intended for function invocation.

* Wed May 22 2013 Petr Machata <pmachata@redhat.com> - 4.1-1.20130314
- Rebase to 4.1 update 3

* Fri Feb 15 2013 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 4.0-7.20120408
- Rebuilt for https://fedoraproject.org/wiki/Fedora_19_Mass_Rebuild

* Tue Aug 28 2012 Petr Machata <pmachata@redhat.com> - 4.0-6.20120408
- Fix build on PowerPC

* Sat Jul 21 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 4.0-5.20120408
- Rebuilt for https://fedoraproject.org/wiki/Fedora_18_Mass_Rebuild

* Thu Jun  7 2012 Petr Machata <pmachata@redhat.com> - 4.0-4.20120408
- Rebase to 4.0 update 4
- Refresh Getting_Started.pdf, Reference.pdf, Tutorial.pdf
- Provide pkg-config files
- Resolves: #825402

* Thu Apr 05 2012 Karsten Hopp <karsten@redhat.com> 4.0-3.20110809
- tbb builds now on PPC(64)

* Sat Jan 14 2012 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 4.0-2.20110809
- Rebuilt for https://fedoraproject.org/wiki/Fedora_17_Mass_Rebuild

* Tue Oct 18 2011 Petr Machata <pmachata@redhat.com> - 4.0-1.20110809
- Rebase to 4.0
  - Port the mfence patch
  - Refresh the documentation bundle

* Tue Jul 26 2011 Petr Machata <pmachata@redhat.com> - 3.0-1.20110419
- Rebase to 3.0-r6
  - Port both patches
  - Package Design_Patterns.pdf
  - Thanks to Richard Shaw for initial rebase patch
- Resolves: #723043

* Wed Feb 09 2011 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.2-3.20090809
- Rebuilt for https://fedoraproject.org/wiki/Fedora_15_Mass_Rebuild

* Thu Jun 10 2010 Petr Machata <pmachata@redhat.com> - 2.2-2.20090809
- Replace mfence instruction with xchg to make it run on ia32-class
  machines without SSE2.
- Resolves: #600654

* Tue Nov  3 2009 Petr Machata <pmachata@redhat.com> - 2.2-1.20090809
- New upstream 2.2
- Resolves: #521571

* Sun Jul 26 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.1-3.20080605
- Rebuilt for https://fedoraproject.org/wiki/Fedora_12_Mass_Rebuild

* Wed Feb 25 2009 Fedora Release Engineering <rel-eng@lists.fedoraproject.org> - 2.1-2.20080605
- Rebuilt for https://fedoraproject.org/wiki/Fedora_11_Mass_Rebuild

* Fri Jun 13 2008 Petr Machata <pmachata@redhat.com> - 2.1-1.20080605
- New upstream 2.1
  - Drop soname patch, parallel make patch, and GCC 4.3 patch

* Wed Feb 13 2008 Petr Machata <pmachata@redhat.com> - 2.0-4.20070927
- Review fixes
  - Use updated URL
  - More timestamp preservation
- Initial import into Fedora CVS

* Mon Feb 11 2008 Petr Machata <pmachata@redhat.com> - 2.0-3.20070927
- Review fixes
  - Preserve timestamp of installed files
  - Fix soname not to contain "debug"

* Tue Feb  5 2008 Petr Machata <pmachata@redhat.com> - 2.0-2.20070927
- Review fixes
  - GCC 4.3 patchset
  - Add BR util-linux net-tools
  - Add full URL to Source0
  - Build in debug mode to work around problems with GCC 4.3

* Mon Dec 17 2007 Petr Machata <pmachata@redhat.com> - 2.0-1.20070927
- Initial package.
- Using SONAME patch from Debian.
